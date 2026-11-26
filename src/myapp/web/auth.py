from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from myapp.extensions import db
from myapp.models.user import AdminUser, NormalUser

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")

_ROLE_MODELS = {
    "NormalUser": NormalUser,
    "AdminUser": AdminUser,
}


def _find_user_by_email(email: str) -> tuple[NormalUser | AdminUser | None, str | None]:
    normalized = email.strip().lower()
    if not normalized:
        return None, None
    for role_name, model_cls in _ROLE_MODELS.items():
        user = db.session.scalars(
            db.select(model_cls).where(model_cls.email == normalized)
        ).first()
        if user is not None:
            return user, role_name
    return None, None


def get_current_user() -> tuple[NormalUser | AdminUser | None, str | None]:
    user_id = session.get("user_id")
    role_name = session.get("user_role")
    model_cls = _ROLE_MODELS.get(role_name) if isinstance(role_name, str) else None
    if user_id is None or model_cls is None:
        return None, None
    user = db.session.get(model_cls, user_id)
    if user is None:
        return None, None
    return user, role_name


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form.get("email", "")
        password = request.form.get("password", "")
        role = request.form.get("role", "normal").strip().lower()

        if role not in ("normal", "admin"):
            return (
                render_template("auth/register.html", error="Rol inválido."),
                400,
            )

        existing_user, _ = _find_user_by_email(email)
        if existing_user is not None:
            return (
                render_template(
                    "auth/register.html",
                    error="El email ya está registrado.",
                ),
                400,
            )

        model_cls = AdminUser if role == "admin" else NormalUser
        try:
            user = model_cls(email=email, passwordHash=password)
            db.session.add(user)
            db.session.commit()
        except ValueError as exc:
            db.session.rollback()
            return render_template("auth/register.html", error=str(exc)), 400

        session["user_id"] = user.id
        session["user_role"] = type(user).__name__
        flash("Registro exitoso.")
        return redirect(url_for("users.index"))

    return render_template("auth/register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "")
        password = request.form.get("password", "")

        user, role_name = _find_user_by_email(email)
        if user is None or not user.checkPassword(password):
            return (
                render_template("auth/login.html", error="Credenciales inválidas."),
                401,
            )

        session["user_id"] = user.id
        session["user_role"] = role_name
        flash("Sesión iniciada.")
        return redirect(url_for("users.index"))

    return render_template("auth/login.html")


@auth_bp.post("/logout")
def logout():
    session.clear()
    flash("Sesión cerrada.")
    return redirect(url_for("auth.login"))
