from messenger import app, db

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        db.session.commit()
    app.run(host='0.0.0.0')
    