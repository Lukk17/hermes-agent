from src.services.base_service import BaseService
from src.models import ServiceResult
from src.paths import LEAKS_DIR
import subprocess


class LocalLeakService(BaseService):

    def _search_grep(self, query: str, max_results: int = 100) -> list[str]:
        if not LEAKS_DIR.is_dir():
            return []
        try:
            result = subprocess.run(
                ["grep", "-r", "-i", "-F", query, str(LEAKS_DIR)],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.stdout:
                lines = result.stdout.strip().split("\n")
                return [line[:500] for line in lines[:max_results]]
            return []
        except Exception:
            return []

    def _search_hash(self, hash_value: str, max_results: int = 50) -> list[str]:
        if not LEAKS_DIR.is_dir():
            return []
        try:
            result = subprocess.run(
                ["grep", "-r", "-F", hash_value, str(LEAKS_DIR)],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.stdout:
                lines = result.stdout.strip().split("\n")
                return [line[:500] for line in lines[:max_results]]
            return []
        except Exception:
            return []

    def search_by_email(self, email: str) -> ServiceResult:
        matches = self._search_grep(email)
        return ServiceResult(
            source="local_leak_db",
            success=True,
            data={"found": len(matches) > 0, "matches": matches, "count": len(matches)},
        )

    def search_by_username(self, username: str) -> ServiceResult:
        matches = self._search_grep(username)
        return ServiceResult(
            source="local_leak_db",
            success=True,
            data={"found": len(matches) > 0, "matches": matches, "count": len(matches)},
        )

    def search_by_domain(self, domain: str) -> ServiceResult:
        matches = self._search_grep(domain)
        return ServiceResult(
            source="local_leak_db",
            success=True,
            data={"found": len(matches) > 0, "matches": matches, "count": len(matches)},
        )

    def search_by_password_hash(self, hash_value: str) -> ServiceResult:
        matches = self._search_hash(hash_value)
        return ServiceResult(
            source="local_leak_db",
            success=True,
            data={"found": len(matches) > 0, "matches": matches, "count": len(matches)},
        )

    def search_by_phone(self, phone: str) -> ServiceResult:
        matches = self._search_grep(phone)
        return ServiceResult(
            source="local_leak_db",
            success=True,
            data={"found": len(matches) > 0, "matches": matches, "count": len(matches)},
        )


local_leak_service = LocalLeakService()
