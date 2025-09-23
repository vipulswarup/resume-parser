import boto3, os, io

BUCKET = os.environ.get("S3_BUCKET")
if not BUCKET:
    raise RuntimeError("S3_BUCKET env var not set")

s3 = boto3.client("s3")

def upload_bytes(content: bytes, key: str, content_type: str = None, prefix: str = None) -> str:
    # Construct full key with prefix if provided
    full_key = f"{prefix}/{key}" if prefix else key
    
    extra = {"ContentType": content_type} if content_type else {}
    s3.upload_fileobj(io.BytesIO(content), BUCKET, full_key, ExtraArgs=extra)
    return f"s3://{BUCKET}/{full_key}"
