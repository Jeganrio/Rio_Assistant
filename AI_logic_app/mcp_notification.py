from plyer import notification

class NotificationTool:

    name = "notification"

    description = (
        "Desktop notifications and reminders."
    )

    def _ok(self, data=None, message="Success"):
        return {
            "status": "ok",
            "data": data or {},
            "message": message
        }

    def _err(self, message):
        return {
            "status": "error",
            "data": None,
            "message": message
        }

    def run(self,
            title="CUBY",
            message=""):

        try:

            notification.notify(
                title=title,
                message=message,
                timeout=10
            )

            return self._ok(
                message="Notification shown"
            )

        except Exception as e:
            return self._err(str(e))