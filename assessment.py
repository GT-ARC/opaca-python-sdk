import os
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel


class Book(BaseModel):
    """Class representing a single book."""

    isbn: str
    authors: List[str]
    title: str
    year: int
    description: Optional[str]


class BookTemplate(BaseModel):
    """Like book, except ISBN, but all optional, for matching and updating."""

    authors: List[str] = []
    title: str = ""
    year: Optional[int] = None
    description: Optional[str] = None



# for now, using a simple dictionary to store books...
books = {}


app = FastAPI(title="Book Management Service")


@app.post("/books", response_model=str)
async def post_book(book: Book) -> str:
    if book.isbn in books:
        raise http_error(400, "Duplicate ISBN")
    books[book.isbn] = book
    return book.isbn


@app.get("/books/{isbn}", response_model=Book)
async def get_book(isbn: str) -> Book:
    if isbn not in books:
        raise http_error(400, "ISBN not found")
    return books[isbn]


@app.put("/books", response_model=List[Book])
async def find_books(template: BookTemplate) -> List[Book]:
    def match(book):
        return (
            all(any(a in b for b in book.authors) for a in template.authors) and
            (template.title in book.title) and
            (template.year is None or template.year == book.year)
        )

    return [book for book in books.values() if match(book)]


@app.put("/books/{isbn}", response_model=Book)
async def update_book(isbn: str, values: BookTemplate) -> Book:
    if isbn not in books:
        raise http_error(400, "ISBN not found")
    books[isbn] = Book(
        isbn=isbn,
        authors=values.authors or books[isbn].authors,
        title=values.title or books[isbn].title,
        year=values.year or books[isbn].year,
        description=values.description or books[isbn].description
    )
    return books[isbn]


@app.delete("/books/{isbn}", response_model=Optional[Book])
async def delete_book(isbn: str) -> Optional[Book]:
    if isbn in books:
        return books.pop(isbn)
    else:
        return None


def http_error(code: int, cause: str) -> HTTPException:
    return HTTPException(status_code=code, detail={"cause": cause})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)

