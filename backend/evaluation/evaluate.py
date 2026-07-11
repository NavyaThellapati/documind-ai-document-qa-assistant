import asyncio
import json
import time
from dataclasses import asdict, dataclass

from app.services.llm import get_llm_service
from app.services.text_processing import TextSection, split_sections
from app.services.vector_store import RetrievedChunk


@dataclass
class EvaluationCase:
    document_name: str
    document_text: str
    question: str
    expected_document: str
    expected_phrase: str


CASES = [
    EvaluationCase("employee_handbook.txt", "Full-time employees receive 15 days of paid time off each calendar year.", "How many PTO days do employees receive?", "employee_handbook.txt", "15 days"),
    EvaluationCase("product_user_guide.txt", "The portal password reset link expires 30 minutes after it is requested.", "When does the password reset link expire?", "product_user_guide.txt", "30 minutes"),
    EvaluationCase("healthcare_portal_faq.txt", "Most lab results are available in the portal within three business days.", "When are lab results available?", "healthcare_portal_faq.txt", "three business days"),
]


def build_chunks(case: EvaluationCase) -> list[RetrievedChunk]:
    chunks = split_sections([TextSection(case.document_text, None)], chunk_size=240, chunk_overlap=20)
    return [
        RetrievedChunk(
            text=chunk.text,
            document_id=case.document_name,
            document_name=case.document_name,
            page_number=None,
            chunk_number=chunk.chunk_number,
            relevance_score=1.0,
        )
        for chunk in chunks
    ]


async def run_evaluation() -> dict:
    llm = get_llm_service()
    results = []
    for case in CASES:
        started = time.perf_counter()
        chunks = build_chunks(case)
        answer = await llm.answer(case.question, chunks)
        elapsed_ms = round((time.perf_counter() - started) * 1000, 2)
        results.append(
            {
                **asdict(case),
                "answer": answer,
                "response_time_ms": elapsed_ms,
                "correct_document_retrieved": chunks[0].document_name == case.expected_document,
                "expected_phrase_present": case.expected_phrase.lower() in answer.lower(),
                "source_attribution_present": "[1]" in answer,
                "unsupported_answer": "could not find" in answer.lower(),
            }
        )
    summary = {
        "case_count": len(results),
        "correct_document_retrieval_count": sum(item["correct_document_retrieved"] for item in results),
        "source_attribution_count": sum(item["source_attribution_present"] for item in results),
        "unsupported_answer_count": sum(item["unsupported_answer"] for item in results),
        "average_response_time_ms": round(sum(item["response_time_ms"] for item in results) / len(results), 2),
    }
    return {"summary": summary, "results": results}


if __name__ == "__main__":
    print(json.dumps(asyncio.run(run_evaluation()), indent=2))
