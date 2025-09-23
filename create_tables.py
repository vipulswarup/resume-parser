from app.db import engine, Base
# import models so they are registered with Base.metadata
import app.models  # noqa: F401
Base.metadata.create_all(bind=engine)
print("Tables created successfully")
