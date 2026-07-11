from pathlib import Path

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

from app.database.database import SessionLocal
from app.database.models import Donor, Patient



BASE_DIR = Path(__file__).resolve().parent.parent

KNOWLEDGE_FILE = BASE_DIR / "knowledge" / "blood_donation_guidelines.md"

CHROMA_DB_DIR = BASE_DIR / "chroma_db"
COLLECTION_NAME = "bloodbridge_knowledge"


def _load_database_documents():
    db = SessionLocal()

    try:
        documents = []

        donors = db.query(Donor).all()
        for donor in donors:
            documents.append(
                Document(
                    page_content=(
                        "Donor registration record.\n"
                        f"Name: {donor.full_name}\n"
                        f"Phone: {donor.phone_number}\n"
                        f"Gender: {donor.gender}\n"
                        f"Blood group: {donor.blood_group}\n"
                        f"Weight: {donor.weight}\n"
                        f"City: {donor.city}\n"
                        f"State: {donor.state}\n"
                        f"Latitude: {donor.latitude}\n"
                        f"Longitude: {donor.longitude}\n"
                        f"Last donation date: {donor.last_donation_date}\n"
                        f"Currently available: {donor.currently_available}"
                    ),
                    metadata={
                        "source": "database",
                        "record_type": "donor",
                        "record_id": donor.donor_id,
                    },
                )
            )

        patients = db.query(Patient).all()
        for patient in patients:
            documents.append(
                Document(
                    page_content=(
                        "Patient registration record.\n"
                        f"Name: {patient.full_name}\n"
                        f"Phone: {patient.phone_number}\n"
                        f"Gender: {patient.gender}\n"
                        f"Blood group: {patient.blood_group}\n"
                        f"City: {patient.city}\n"
                        f"State: {patient.state}\n"
                        f"Latitude: {patient.latitude}\n"
                        f"Longitude: {patient.longitude}"
                    ),
                    metadata={
                        "source": "database",
                        "record_type": "patient",
                        "record_id": patient.patient_id,
                    },
                )
            )

        return documents
    finally:
        db.close()


def create_vector_store():
    documents = [
        Document(
            page_content=KNOWLEDGE_FILE.read_text(encoding="utf-8"),
            metadata={"source": str(KNOWLEDGE_FILE)},
        )
    ]
    documents.extend(_load_database_documents())

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=50,
    )

    chunks = splitter.split_documents(documents)

    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    existing_store = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=str(CHROMA_DB_DIR),
    )

    try:
        existing_store.delete_collection()
    except Exception:
        pass

    vector_store = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=str(CHROMA_DB_DIR),
        collection_name=COLLECTION_NAME,
    )

    print(f"Created {len(chunks)} vector-store chunks.")

    return vector_store
