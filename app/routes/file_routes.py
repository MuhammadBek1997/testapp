from fastapi import APIRouter, UploadFile, HTTPException, Form, Depends, File, Query
from typing import List, Optional
from sqlalchemy.orm import Session
from bs4 import BeautifulSoup
from app.s3 import upload_to_s3
from app.utils import find_red_class
from app.database import get_db
from app.models import Question
import zipfile, shutil, os, tempfile

router = APIRouter()

@router.post("/upload/")
async def upload_zips(
    files: List[UploadFile] = File(...),
    categories: List[str] = Form(...),
    subjects: List[str] = Form(...),
    db: Session = Depends(get_db),
):
    if len(files) != len(categories) or len(files) != len(subjects):
        raise HTTPException(status_code=400, detail="Fayllar, kategoriyalar va mavzular soni bir xil bo'lishi kerak")

    for file, category, subject in zip(files, categories, subjects):
        content = await file.read()
        tmp_upload = tempfile.NamedTemporaryFile(delete=False)
        tmp_upload.write(content)
        tmp_upload.flush()
        tmp_upload.close()

        extract_dir = tempfile.mkdtemp(prefix="extracted_")
        with zipfile.ZipFile(tmp_upload.name, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)

        html_file_path = None
        for root, dirs, files_in in os.walk(extract_dir):
            for f in files_in:
                if f.endswith(".html"):
                    html_file_path = os.path.join(root, f)
                    break
            if html_file_path:
                break

        if not html_file_path:
            raise HTTPException(status_code=400, detail=f"No HTML file found in the ZIP archive: {file.filename}.")

        with open(html_file_path, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f, "html.parser")

        paragraphs = soup.find_all("p", class_=lambda x: x and x.startswith("c"))
        red_class = find_red_class(soup)
        current_block = {"question": None, "variants": [], "correct_answer": None, "image": None}

        for paragraph in paragraphs:
            text = paragraph.get_text(strip=True)
            if not text:
                continue

            img_tag = paragraph.find("img")
            if img_tag:
                img_src = img_tag["src"]
                image_src = next((os.path.join(r, f) for r, d, files_in in os.walk(extract_dir) for f in files_in if f == os.path.basename(img_src)), None)
                if image_src:
                    s3_url = upload_to_s3(image_src, f"images/{os.path.basename(image_src)}")
                    current_block["image"] = s3_url

            if text[0].isdigit() and "." in text:
                if current_block["question"]:
                    unique_variants = list(dict.fromkeys(current_block["variants"]))
                    options_text = ", ".join(unique_variants)
                    q = Question(
                        text=current_block["question"],
                        options=options_text,
                        true_answer=current_block["correct_answer"],
                        image=current_block["image"],
                        category=category,
                        subject=subject,
                    )
                    db.add(q)
                    db.commit()
                current_block = {"question": text, "variants": [], "correct_answer": None, "image": None}
            elif text.startswith(("A)", "B)", "C)", "D)")):
                current_block["variants"].append(text)
                span_tags = paragraph.find_all("span")
                for span in span_tags:
                    if red_class in span.get("class", []):
                        current_block["correct_answer"] = span.get_text(strip=True)[0]

        if current_block["question"]:
            options_text = "\n".join(current_block["variants"])
            q = Question(
                text=current_block["question"],
                options=options_text,
                true_answer=current_block["correct_answer"],
                image=current_block["image"],
                category=category,
                subject=subject,
            )
            db.add(q)
            db.commit()

        shutil.rmtree(extract_dir, ignore_errors=True)
        os.remove(tmp_upload.name)

    return {"message": "Fayllar muvaffaqiyatli yuklandi"}

def _parse_options(options_text: str):
    parts = [p.strip() for p in (options_text.split("\n") if "\n" in options_text else options_text.split(",")) if p.strip()]
    letters = ["A", "B", "C", "D"]
    cleaned = []
    for p in parts:
        if len(p) > 2 and p[1] == ")" and p[0] in letters:
            cleaned.append(p[3:].strip())
        else:
            cleaned.append(p)
    return cleaned

@router.get("/questions")
def get_questions(category: Optional[str] = Query(None), subject: Optional[str] = Query(None), db: Session = Depends(get_db)):
    query = []
    if category:
        query.append(Question.category == category)
    if subject:
        query.append(Question.subject == subject)
    q = db.query(Question)
    if query:
        from sqlalchemy import and_
        q = q.filter(and_(*query))
    items = q.all()
    result = []
    for it in items:
        options = _parse_options(it.options or "")
        true = it.true_answer
        idx = None
        if true in ["A", "B", "C", "D"]:
            letters = ["A", "B", "C", "D"]
            try:
                idx = letters.index(true)
            except ValueError:
                idx = None
        result.append({
            "id": str(it.id),
            "question": it.text,
            "options": options,
            "correctAnswer": idx if idx is not None else 0,
        })
    return result