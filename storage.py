"""Audio storage: Amazon S3 when S3_BUCKET is set, otherwise a local folder."""
import os


class LocalStorage:
    def __init__(self, root):
        self.root = root

    def _path(self, key):
        path = os.path.abspath(os.path.join(self.root, key))
        if not path.startswith(os.path.abspath(self.root) + os.sep):
            raise ValueError("bad key")
        return path

    def put(self, key, data):
        path = self._path(key)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(data)

    def get(self, key):
        with open(self._path(key), "rb") as f:
            return f.read()

    def delete(self, key):
        try:
            os.remove(self._path(key))
        except FileNotFoundError:
            pass


class S3Storage:
    def __init__(self, bucket, region):
        import boto3

        self.bucket = bucket
        # Credentials come from the EC2 instance role; no keys in code.
        self.client = boto3.client("s3", region_name=region)

    def put(self, key, data):
        self.client.put_object(Bucket=self.bucket, Key=key, Body=data,
                               ContentType="audio/wav", ServerSideEncryption="AES256")

    def get(self, key):
        return self.client.get_object(Bucket=self.bucket, Key=key)["Body"].read()

    def delete(self, key):
        self.client.delete_object(Bucket=self.bucket, Key=key)


def make_storage(config):
    if config.get("S3_BUCKET"):
        return S3Storage(config["S3_BUCKET"], config["AWS_REGION"])
    return LocalStorage(config["LOCAL_AUDIO_DIR"])
