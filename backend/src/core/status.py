from fastapi.responses import JSONResponse


class APIStatus:
    registry = {}

    def __init__(self, http, message, color, bg):
        self.http = http
        self.message = message
        self.color = color
        self.bg = bg

        APIStatus.registry[http] = self

    # Return all API statuses
    @classmethod
    def all(cls):
        return list(cls.registry.values())

    # Get exact match (like ORM get)
    @classmethod
    def get(cls, http: int):
        return cls.registry.get(http, None)

    # Filter with "contains" support
    @classmethod
    def filter(cls, **kwargs):
        results = cls.registry.values()

        for key, value in kwargs.items():
            if "__contains" in key:
                attr = key.split("__")[0]
                results = [
                    s for s in results
                    if value.lower() in getattr(s, attr).lower()
                ]
            else:
                results = [
                    s for s in results
                    if getattr(s, key) == value
                ]
        return list(results)
    
    def to_dict(self):
        """Return status as a dictionary"""
        return {
            "status_code": self.http,
            "message": self.message,
            "color": self.color,
            "bg": self.bg
        }

    # Check if exists
    @classmethod
    def exists(cls, **kwargs):
        return cls.get(**kwargs) is not None

    # Insert all predefined API statuses
    @classmethod
    def insert(cls):
        # 2xx
        cls(200, "Request successful", "#2e7d32", "#e8f5e9")
        cls(201, "Resource created successfully", "#2e7d32", "#e8f5e9")
        cls(200, "Resource updated successfully", "#1565c0", "#e3f2fd")
        cls(200, "Resource deleted successfully", "#c62828", "#ffebee")
        cls(202, "Request accepted for processing", "#0277bd", "#e1f5fe")
        cls(204, "No content", "#424242", "#fafafa")

        # Listing
        cls(200, "List fetched successfully", "#1565c0", "#e3f2fd")
        cls(200, "Paginated data fetched successfully", "#1565c0", "#e3f2fd")

        # 4xx
        cls(400, "Bad request", "#ef6c00", "#fff3e0")
        cls(401, "Unauthorized", "#c62828", "#ffebee")
        cls(403, "Forbidden", "#6a1b9a", "#f3e5f5")
        cls(404, "Resource not found", "#616161", "#f5f5f5")
        cls(405, "Method not allowed", "#ad1457", "#fce4ec")
        cls(409, "Resource already exists", "#ef6c00", "#fff3e0")
        cls(413, "Payload too large", "#4e342e", "#efebe9")
        cls(415, "Unsupported media type", "#4a148c", "#f3e5f5")

        # Validation
        cls(422, "Validation error", "#ad1457", "#fce4ec")
        cls(422, "Unprocessable entity", "#ad1457", "#fce4ec")

        # Token / Auth errors
        cls(498, "Invalid token", "#b71c1c", "#ffebee")
        cls(499, "Token expired", "#b71c1c", "#ffebee")
        cls(440, "Session expired", "#b71c1c", "#ffebee")

        # Rate limit
        cls(429, "Too many requests", "#d84315", "#ffccbc")

        # 5xx
        cls(500, "Internal server error", "#b71c1c", "#ffebee")
        cls(501, "Not implemented", "#4e342e", "#efebe9")
        cls(503, "Service unavailable", "#6d4c41", "#efebe9")
        cls(504, "Gateway timeout", "#4a148c", "#f3e5f5")




class DBStatus:
    registry = {}

    def __init__(self, code, message, color, bg):
        self.code = code
        self.message = message
        self.color = color
        self.bg = bg

        DBStatus.registry[code] = self

    # Return all statuses
    @classmethod
    def all(cls):
        return list(cls.registry.values())

    # Get by exact match
    @classmethod
    def get(cls, code: int):
        return cls.registry.get(code, None)
    
    def to_dict(self):
        """Return status as a dictionary"""
        return {
            "status": self.code,
            "message": self.message,
            "color": self.color,
            "bg": self.bg
        }

    # Filter with supports contains
    @classmethod
    def filter(cls, **kwargs):
        results = cls.registry.values()

        for key, value in kwargs.items():
            if "__contains" in key:
                attr = key.split("__")[0]
                results = [s for s in results if value.lower() in getattr(s, attr).lower()]
            else:
                results = [s for s in results if getattr(s, key) == value]

        return list(results)
        

    # Insert predefined statuses
    @classmethod
    def insert(cls):
        cls(1000, "Operation successful", "#2e7d32", "#e8f5e9")
        cls(1001, "Record created successfully", "#1b5e20", "#e8f5e9")
        cls(1002, "Record updated successfully", "#1565c0", "#e3f2fd")
        cls(1003, "Record deleted successfully", "#c62828", "#ffebee")

        cls(1404, "Record not found", "#616161", "#f5f5f5")
        cls(1409, "Record already exists", "#ef6c00", "#fff3e0")
        cls(1400, "Invalid data provided", "#ad1457", "#fce4ec")

        cls(1500, "Database connection failed", "#b71c1c", "#ffebee")
        cls(1501, "Database transaction failed", "#9c27b0", "#f3e5f5")
        cls(1502, "Constraint violation", "#d84315", "#fbe9e7")
        cls(1503, "Database operation timed out", "#4e342e", "#efebe9")
        cls(1504, "Permission denied", "#6a1b9a", "#f3e5f5")

    # Check if exists
    @classmethod
    def exists(cls, **kwargs):
        return cls.get(**kwargs) is not None



def api_response(status_code: int, data=None, message=None, **kwargs):
        status_obj = APIStatus.get(status_code).to_dict()

        if message:
            status_obj["message"] = message

        if data is not None:
            status_obj["data"] = data

        return JSONResponse(
            status_code=status_code,
            content=status_obj,
            **kwargs
        )