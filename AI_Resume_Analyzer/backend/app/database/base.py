# Import Base and all models to ensure they are registered for migrations/creation
from app.database.connection import Base
from app.models.user import User, UploadedPDF
