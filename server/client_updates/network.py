import threading
import requests
import queue
import json

class NetworkManager:
    def __init__(self):
        # self.base_url = "http://127.0.0.1:8002"
        self.base_url = "https://polygon-rush-server.onrender.com"
        self.token = None
        self.username = None
        self.result_queue = queue.Queue()
        
    def _make_request(self, method, endpoint, data, callback):
        try:
            url = f"{self.base_url}{endpoint}"
            headers = {}
            if self.token:
                headers["Authorization"] = f"Bearer {self.token}"
                
            if method == "GET":
                response = requests.get(url, headers=headers, params=data, timeout=60)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=data, timeout=60)
            elif method == "PUT":
                response = requests.put(url, headers=headers, json=data, timeout=60)
            elif method == "DELETE":
                response = requests.delete(url, headers=headers, timeout=60)
                
            result = {
                "success": response.status_code in (200, 201),
                "status_code": response.status_code,
                "data": response.json() if response.content else {}
            }
            if not result["success"]:
                print(f"API Error {response.status_code}: {response.text}")
        except Exception as e:
            print(f"Network Request Exception: {e}")
            result = {
                "success": False,
                "status_code": 0,
                "error": "Cannot connect to server"
            }
            
        self.result_queue.put((callback, result))

    def update(self):
        """Call this every frame to process callbacks from network threads"""
        while True:
            try:
                callback, result = self.result_queue.get_nowait()
            except queue.Empty:
                break
            if callback:
                try:
                    callback(result)
                except Exception as e:
                    import traceback
                    print(f"Network callback error: {e}")
                    traceback.print_exc()

    def register(self, username, password, callback):
        t = threading.Thread(target=self._make_request, args=("POST", "/register", {"username": username, "password": password}, callback))
        t.daemon = True
        t.start()
        
    def login(self, username, password, callback):
        def intercept_callback(result):
            if result.get("success") and "access_token" in result.get("data", {}):
                self.token = result["data"]["access_token"]
                self.username = username
            if callback:
                callback(result)
                
        t = threading.Thread(target=self._make_request, args=("POST", "/login", {"username": username, "password": password}, intercept_callback))
        t.daemon = True
        t.start()
        
    def logout(self):
        self.token = None
        self.username = None
        self.username = None

    def get_levels(self, filter_by="newest", skip=0, limit=50, callback=None):
        t = threading.Thread(target=self._make_request, args=("GET", "/levels", {"filter_by": filter_by, "skip": skip, "limit": limit}, callback))
        t.daemon = True
        t.start()

    def check_update(self, callback):
        t = threading.Thread(target=self._make_request, args=("GET", "/version", None, callback))
        t.daemon = True
        t.start()

    def download_update(self, callback, filename="main.py"):
        def _download():
            try:
                response = requests.get(f"{self.base_url}/download_update", params={"file": filename}, timeout=15)
                if response.status_code == 200:
                    callback({"success": True, "text": response.text})
                else:
                    callback({"success": False, "error": f"HTTP {response.status_code}"})
            except Exception as e:
                callback({"success": False, "error": str(e)})
        t = threading.Thread(target=_download)
        t.daemon = True
        t.start()

    def get_level_data(self, level_id, callback):
        t = threading.Thread(target=self._make_request, args=("GET", f"/levels/{level_id}", None, callback))
        t.daemon = True
        t.start()

    def get_user_profile(self, username, callback):
        t = threading.Thread(target=self._make_request, args=("GET", f"/users/{username}", None, callback))
        t.daemon = True
        t.start()

    def update_icons(self, profile_data, callback):
        t = threading.Thread(target=self._make_request, args=("PUT", "/users/me/icons", profile_data, callback))
        t.daemon = True
        t.start()

    def upload_level(self, title, data_str, suggested_difficulty, level_id=None, callback=None):
        payload = {
            "title": title,
            "data": data_str,
            "suggested_difficulty": suggested_difficulty
        }
        if level_id:
            payload["level_id"] = level_id
            
        t = threading.Thread(target=self._make_request, args=("POST", "/levels/upload", payload, callback))
        t.daemon = True
        t.start()

    def rate_level(self, version_id, rating, callback):
        t = threading.Thread(target=self._make_request, args=("POST", f"/level_versions/{version_id}/rate", {"rating": rating}, callback))
        t.daemon = True
        t.start()
        
    def like_level(self, level_id, is_like, callback):
        t = threading.Thread(target=self._make_request, args=("POST", f"/levels/{level_id}/like?is_like={str(is_like).lower()}", None, callback))
        t.daemon = True
        t.start()
        
    def delete_level(self, level_id, callback):
        t = threading.Thread(target=self._make_request, args=("DELETE", f"/levels/{level_id}", None, callback))
        t.daemon = True
        t.start()
        
    def complete_level_version(self, version_id, callback):
        t = threading.Thread(target=self._make_request, args=("POST", f"/level_versions/{version_id}/complete", None, callback))
        t.daemon = True
        t.start()

    def comment_level(self, level_id, text, callback):
        t = threading.Thread(target=self._make_request, args=("POST", f"/levels/{level_id}/comment", {"text": text}, callback))
        t.daemon = True
        t.start()

    def get_comments(self, level_id, callback):
        t = threading.Thread(target=self._make_request, args=("GET", f"/levels/{level_id}/comments", None, callback))
        t.daemon = True
        t.start()

    def get_users(self, search, callback):
        endpoint = "/users"
        if search: endpoint += f"?search={search}"
        t = threading.Thread(target=self._make_request, args=("GET", endpoint, None, callback))
        t.daemon = True
        t.start()

    def moderate_level(self, version_id, status, stars, callback):
        t = threading.Thread(target=self._make_request, args=("POST", f"/level_versions/{version_id}/moderate?status={status}&stars={stars}", None, callback))
        t.daemon = True
        t.start()

    def get_sent_levels(self, callback):
        t = threading.Thread(target=self._make_request, args=("GET", "/admin/sent_levels", None, callback))
        t.daemon = True
        t.start()

    def admin_update_stats(self, username, stat_changes, callback):
        t = threading.Thread(target=self._make_request, args=("POST", f"/admin/users/{username}/stats", stat_changes, callback))
        t.daemon = True
        t.start()

    def admin_set_user_mod(self, username, is_mod, callback):
        t = threading.Thread(target=self._make_request, args=("POST", f"/admin/users/{username}/mod", {"is_moderator": is_mod}, callback))
        t.daemon = True
        t.start()

    def admin_ban_user(self, username, callback):
        t = threading.Thread(target=self._make_request, args=("POST", f"/admin/users/{username}/ban", None, callback))
        t.daemon = True
        t.start()

    def delete_own_account(self, callback):
        t = threading.Thread(target=self._make_request, args=("DELETE", "/users/me", None, callback))
        t.daemon = True
        t.start()
