from flask import Flask, jsonify

from config import Config
from services.gmail_service import GmailService


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    Config.validate()

    @app.get("/health")
    def health_check():
        return jsonify({"status": "ok"}), 200

    @app.post("/process-unread-emails")
    def process_unread_emails():
        gmail_service = GmailService(
            email_user=app.config["EMAIL_USER"],
            email_pass=app.config["EMAIL_PASS"],
        )
        results = gmail_service.process_unread_emails()
        return jsonify(
            {
                "processed_count": len(results),
                "results": results,
            }
        ), 200

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
