import json
import os
import uuid
from datetime import UTC, datetime
from typing import Any

from app.config import settings
from app.models import SolveRequest
from app.services.aws_math_solver import AwsMathSolver


class SolveJobService:
    def __init__(self) -> None:
        try:
            import boto3  # noqa: PLC0415 — AWS-only; lazy import for non-AWS environments
            from botocore.exceptions import ClientError as _ClientError  # noqa: F401
        except ImportError as exc:
            raise RuntimeError(
                "boto3 is required for SolveJobService but is not installed"
            ) from exc

        bucket = settings.images_bucket_name
        if not bucket:
            raise RuntimeError("IMAGES_BUCKET_NAME is required for async solve jobs")
        self.bucket = bucket
        self.prefix = "solve-jobs"
        self.s3 = boto3.client("s3", region_name=settings.aws_region)
        self.lambda_client = boto3.client("lambda", region_name=settings.aws_region)

    def _key(self, job_id: str) -> str:
        return f"{self.prefix}/{job_id}.json"

    def _now(self) -> str:
        return datetime.now(UTC).isoformat()

    def _put_job(self, key: str, payload: dict[str, Any]) -> None:
        self.s3.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            ContentType="application/json",
        )

    def _get_job(self, key: str) -> dict[str, Any]:
        obj = self.s3.get_object(Bucket=self.bucket, Key=key)
        body = obj["Body"].read().decode("utf-8")
        return json.loads(body)

    def create_job(self, request: SolveRequest) -> dict[str, Any]:
        job_id = f"job_{uuid.uuid4().hex}"
        key = self._key(job_id)
        created_at = self._now()

        record = {
            "jobId": job_id,
            "status": "queued",
            "createdAt": created_at,
            "updatedAt": created_at,
            "request": request.model_dump(by_alias=True),
            "result": None,
            "error": None,
        }
        self._put_job(key, record)

        function_name = os.getenv("AWS_LAMBDA_FUNCTION_NAME")
        if not function_name:
            raise RuntimeError("AWS_LAMBDA_FUNCTION_NAME is not set")

        self.lambda_client.invoke(
            FunctionName=function_name,
            InvocationType="Event",
            Payload=json.dumps(
                {
                    "source": "solve.jobs",
                    "action": "process",
                    "jobId": job_id,
                    "bucket": self.bucket,
                    "key": key,
                }
            ).encode("utf-8"),
        )

        return {
            "jobId": job_id,
            "status": "queued",
            "pollUrl": f"/v1/solve-jobs/{job_id}",
            "createdAt": created_at,
        }

    def get_job(self, job_id: str) -> dict[str, Any]:
        from botocore.exceptions import ClientError  # noqa: PLC0415

        key = self._key(job_id)
        try:
            job = self._get_job(key)
            job.pop("request", None)
            return job
        except ClientError as exc:
            error_code = (exc.response.get("Error") or {}).get("Code")
            if error_code in {"NoSuchKey", "404"}:
                raise FileNotFoundError(job_id) from exc
            raise

    def process_job_event(self, event: dict[str, Any]) -> dict[str, Any]:
        key = str(event.get("key") or "").strip()
        if not key:
            raise ValueError("key is required")

        record = self._get_job(key)
        status = str(record.get("status") or "")
        if status in {"succeeded", "failed"}:
            return {"ok": True, "jobId": record.get("jobId"), "status": status}

        now = self._now()
        record["status"] = "running"
        record["updatedAt"] = now
        record["startedAt"] = now
        self._put_job(key, record)

        try:
            request = SolveRequest.model_validate(record.get("request") or {})
            solver = AwsMathSolver()
            result = solver.solve(request)

            completed_at = self._now()
            record["status"] = "succeeded"
            record["updatedAt"] = completed_at
            record["completedAt"] = completed_at
            record["result"] = result.model_dump(by_alias=True)
            record["error"] = None
            self._put_job(key, record)
            return {
                "ok": True,
                "jobId": record.get("jobId"),
                "status": "succeeded",
            }
        except Exception as exc:
            failed_at = self._now()
            record["status"] = "failed"
            record["updatedAt"] = failed_at
            record["completedAt"] = failed_at
            record["error"] = str(exc)
            self._put_job(key, record)
            return {
                "ok": False,
                "jobId": record.get("jobId"),
                "status": "failed",
                "error": str(exc),
            }
