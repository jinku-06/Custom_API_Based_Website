from flask import Flask, redirect, render_template, request, flash, session
import requests
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
import os

# ----------------------------- Configs
TRACE_MOE_API = "https://api.trace.moe/search"
ANILIST_API = "https://graphql.anilist.co"
UPLOAD_FOLDER = "static/uploads"
MAX_CONTENT_LENGTH = 16 * 1024 * 1024
SECRET_KEY = "YOUR_SECRET_KEY"


# -------------------------------FLASK APP CONFIG

app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH
app.config["SECRET_KEY"] = SECRET_KEY


# -------------------------------------GraphQL query
query = """
query ($id: Int) { 
  Media (id: $id, type: ANIME) { 
    id
    title {
      romaji
      english
      native
    }
    episodes
    genres
    duration
    siteUrl
    format
    coverImage {  
      extraLarge
      large
      medium
      color
    }
  }
}
"""


# ---------------------------------upload directory
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)


# -------------------------------------HOME ROUTE
@app.route("/", methods=["GET", "POST"])
def home():
    data = None
    anime_data = None
    file_path = None
    if request.method == "POST":
        file = request.files.get("file")
        if file:
            try:
                file_path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
                file.save(file_path)

                # --------------------------------GET TRACE_MOE_API
                with open(file_path, mode="rb") as img_file:
                    response = requests.post(TRACE_MOE_API, files={"image": img_file})
                    response.raise_for_status()
                    result = response.json().get("result", [])

                    if result:
                        similarity_values = [
                            round(item["similarity"] * 100, 2) for item in result
                        ]
                        max_value = max(similarity_values)
                        index = similarity_values.index(max_value)
                        data = result[index]

                        # -------------------------------------------GET ANILIST_API
                        variables = {"id": data["anilist"]}
                        anilist_response = requests.post(
                            ANILIST_API, json={"query": query, "variables": variables}
                        )
                        anilist_response.raise_for_status()
                        anime_data = anilist_response.json().get("data")

            except requests.RequestException as e:
                flash(f"An error occurred: {e}", "error")
            except Exception as e:
                flash(f"An unexpected error occurred: {e}", "error")

            # ----------------------REMOVING THE UPLOADED IMG AFTER GETTING THE DATA OR WHEN ANY ERROR OCCURS
            finally:
                if file_path and os.path.exists(file_path):
                    os.remove(file_path)

    return render_template("index.html", data=data, anime_data=anime_data)


if __name__ == "__main__":
    app.run(debug=True)
