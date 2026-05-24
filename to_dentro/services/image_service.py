import cloudinary.uploader
from typing import Optional

def upload_image(file, folder: str = "to-dentro-app") -> Optional[str]:
    """
    Uploads an image file to Cloudinary and returns its secure URL.
    :param file: The file-like object to upload.
    :param folder: The Cloudinary folder to store the image in.
    :return: The secure URL of the uploaded image, or None if it failed.
    """

    if not file:
        return None

    try:
        result = cloudinary.uploader.upload(
            file,
            folder=folder,
            resource_type="image"
        )
        return result.get("secure_url")
    except Exception as e:
        print(f"Error uploading image to Cloudinary: {e}")
        return None

def delete_image(public_id: str) -> bool:
    """
    Deletes an image from Cloudinary by its public ID.
    :param public_id: The public ID of the image to delete.
    :return: True if successfully deleted, False otherwise.
    """
    try:
        result = cloudinary.uploader.destroy(public_id)
        return result.get('result') == 'ok'
    except Exception as e:
        print(f"Error deleting image from Cloudinary: {e}")
        return False
