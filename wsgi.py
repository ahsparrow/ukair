from ukair import create_app

application = create_app("UKAIR_CONFIG")

if __name__ == "__main__":
    application.run()
