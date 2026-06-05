import ast
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent


def _python_files():
    ignored_parts = {"__pycache__", ".pytest_cache", ".mypy_cache"}
    return [
        path
        for path in BACKEND_ROOT.rglob("*.py")
        if not ignored_parts.intersection(path.parts)
    ]


def _module_ast(relative_path: str) -> ast.Module:
    return ast.parse((BACKEND_ROOT / relative_path).read_text(), filename=relative_path)


def test_orders_router_uses_shared_gateway_user_uuid_parser():
    tree = _module_ast("app/routers/orders.py")

    function_names = {
        node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
    }
    assert "_parse_user_uuid" not in function_names

    imported_names = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module == "app.dependencies"
        for alias in node.names
    }
    assert "parse_gateway_user_uuid" in imported_names

    called_names = [
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    ]
    assert called_names.count("parse_gateway_user_uuid") >= 3


def test_backend_does_not_define_local_audit_or_token_revocation_stores():
    forbidden_files = [
        BACKEND_ROOT / "app/audit.py",
        BACKEND_ROOT / "app/revocation.py",
    ]
    assert [path for path in forbidden_files if path.exists()] == []

    forbidden_imports = {"app.audit", "app.revocation"}
    offenders = []
    for path in _python_files():
        if path == Path(__file__).resolve():
            continue
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module in forbidden_imports:
                offenders.append(f"{path.relative_to(REPO_ROOT)} imports {node.module}")
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name in forbidden_imports:
                        offenders.append(f"{path.relative_to(REPO_ROOT)} imports {alias.name}")

    assert offenders == []


def test_readme_documents_gateway_owned_audit_and_revocation_policy():
    readme = (REPO_ROOT / "README.md").read_text()

    assert "監査ログ" in readme
    assert "トークン失効" in readme
    assert "APIゲートウェイ側の責務" in readme
    assert "独自の失効管理は行いません" in readme


def test_unused_auth_token_schemas_are_removed():
    tree = _module_ast("app/schemas.py")
    class_names = {
        node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)
    }

    assert class_names.isdisjoint(
        {
            "UserRegister",
            "UserLogin",
            "TokenResponse",
            "TokenRefreshRequest",
            "AccessTokenResponse",
        }
    )


def test_service_authorization_modules_are_removed():
    authorization_modules = sorted(
        path.relative_to(REPO_ROOT).as_posix()
        for path in (BACKEND_ROOT / "app/services").glob("*/authorization.py")
    )

    assert authorization_modules == []


def test_east_west_payment_helpers_are_marked_as_samples_not_production_contracts():
    payment_client = (
        BACKEND_ROOT / "app/services/order_service/payment_client.py"
    ).read_text()
    transport = (BACKEND_ROOT / "app/services/payment_service/transport.py").read_text()

    assert "サンプル実装" in payment_client
    assert "east-west 認証チェーン" in payment_client
    assert "X-Forwarded-Token" in payment_client
    assert "production 利用" in payment_client

    assert "X-Forwarded-Token" in transport
    assert "未実装" in transport


def test_gateway_policy_api_paths_are_defined_as_module_constants():
    policy_path = BACKEND_ROOT / "app/gateway/policy.py"
    tree = ast.parse(policy_path.read_text(), filename=str(policy_path))

    top_level_api_constants = {
        target.id
        for node in tree.body
        if isinstance(node, ast.Assign)
        for target in node.targets
        if isinstance(target, ast.Name)
        and target.id.isupper()
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
        and node.value.value.startswith("/api/")
    }
    assert top_level_api_constants

    gateway_policy_class = next(
        node
        for node in tree.body
        if isinstance(node, ast.ClassDef) and node.name == "GatewayPolicy"
    )
    method_path_literals = sorted(
        {
            node.value
            for node in ast.walk(gateway_policy_class)
            if isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and node.value.startswith("/api/")
        }
    )

    assert method_path_literals == []
