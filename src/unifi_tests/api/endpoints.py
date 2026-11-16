"""All UniFi OS REST paths in one place.

UniFi OS has no official public API for user management. The paths below are the ones
the UniFi OS web UI itself calls (verified against UniFi OS Server 5.1.42 with the browser
DevTools; the e2e run also records them to reports/network.har). When Ubiquiti changes
them, this is the only file to edit.
"""

# UniFi OS core (auth)
LOGIN = "/api/auth/login"
LOGOUT = "/api/auth/logout"
CURRENT_USER = "/api/users/self"

# Users app ("Admins & Users") behind the UniFi OS proxy.
# Responses are wrapped as {"code": 1, "codeS": "SUCCESS", "msg": ..., "data": ...};
# application errors come back as HTTP 200 with code != 1.
USERS = "/proxy/users/api/v2/users"
USER_CREATE = "/proxy/users/api/v2/user"
USER = "/proxy/users/api/v2/user/{user_id}"
ROLES = "/proxy/users/api/v2/roles"
