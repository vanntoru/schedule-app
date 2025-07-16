from schedule_app.cli import shell
import code

def test_shell_invokes_interact(monkeypatch):
    called = {}

    def fake_interact(*, local=None):
        called['local'] = local

    monkeypatch.setattr(code, 'interact', fake_interact)
    shell()
    assert 'create_app' in called['local']
