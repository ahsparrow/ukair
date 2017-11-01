from ukair import create_app

if __name__ == "__main__":
    app = create_app("UKAIR_CONFIG")
    app.run()
