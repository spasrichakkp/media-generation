import sys
import os
from unittest.mock import MagicMock

# Add backend to path
sys.path.append(os.path.abspath("backend"))

from src.infrastructure.repositories import PostgresUserRepository, PostgresJobRepository
from src.domain.repositories import UserRepository, JobRepository

def verify_implementations():
    print("Verifying implementations...")
    
    # Mock session
    session = MagicMock()
    
    # Instantiate repositories
    try:
        user_repo = PostgresUserRepository(session)
        print("✅ PostgresUserRepository instantiated successfully")
    except TypeError as e:
        print(f"❌ PostgresUserRepository instantiation failed: {e}")
        
    try:
        job_repo = PostgresJobRepository(session)
        print("✅ PostgresJobRepository instantiated successfully")
    except TypeError as e:
        print(f"❌ PostgresJobRepository instantiation failed: {e}")
        
    # Check inheritance
    if issubclass(PostgresUserRepository, UserRepository):
        print("✅ PostgresUserRepository inherits from UserRepository")
    else:
        print("❌ PostgresUserRepository does not inherit from UserRepository")
        
    if issubclass(PostgresJobRepository, JobRepository):
        print("✅ PostgresJobRepository inherits from JobRepository")
    else:
        print("❌ PostgresJobRepository does not inherit from JobRepository")

if __name__ == "__main__":
    verify_implementations()
