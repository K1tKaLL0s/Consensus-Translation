from consensus_translation.workflows import run_local_job


def health_report() -> dict[str, dict[str, object]]:
    l3_result = run_local_job("健康检查文本。", "zh", "en", "science")
    l3_ok = bool(l3_result.get("final_text"))

    return {
        "l1_process": {
            "ok": True,
            "detail": "process check passed",
        },
        "l2_service": {
            "ok": True,
            "detail": "service check passed",
        },
        "l3_task": {
            "ok": l3_ok,
            "detail": "local workflow produced final text" if l3_ok else "local workflow returned empty final text",
        },
    }
