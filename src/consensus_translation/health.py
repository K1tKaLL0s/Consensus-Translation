import importlib.util

from consensus_translation.workflows import run_local_job


def health_report() -> dict[str, dict[str, object]]:
    streamlit_available = importlib.util.find_spec("streamlit") is not None
    l1_detail = (
        "streamlit import available"
        if streamlit_available
        else "streamlit import unavailable"
    )

    try:
        l2_result = run_local_job("service-check", "zh", "en", "health")
        l2_ok = bool(l2_result.get("contract"))
        l2_detail = "workflow service check passed" if l2_ok else "workflow service missing contract"
    except Exception as exc:
        l2_ok = False
        l2_detail = f"workflow service check failed: {exc}"

    try:
        l3_result = run_local_job("健康检查文本。", "zh", "en", "science")
        l3_ok = bool(l3_result.get("final_text"))
        l3_detail = (
            "local workflow produced final text"
            if l3_ok
            else "local workflow returned empty final text"
        )
    except Exception as exc:
        l3_ok = False
        l3_detail = f"local workflow smoke failed: {exc}"

    return {
        "l1_process": {
            "ok": streamlit_available,
            "detail": l1_detail,
        },
        "l2_service": {
            "ok": l2_ok,
            "detail": l2_detail,
        },
        "l3_task": {
            "ok": l3_ok,
            "detail": l3_detail,
        },
    }
