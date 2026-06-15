from __future__ import annotations

import json

import pytest

from account_store import AccountConfig, CaughtStore, _safe_account, delete_account_data

# --- account name sanitizing ---


def test_safe_account_keeps_plain_names():
    assert _safe_account("Ash") == "Ash"
    assert _safe_account("Ghost_Pixxel-1") == "Ghost_Pixxel-1"


def test_safe_account_replaces_unsafe_chars():
    assert _safe_account("My Account!") == "My_Account_"
    assert _safe_account("a/b\\c") == "a_b_c"


def test_safe_account_rejects_empty_or_dots():
    for bad in ("", "   ", "..", "."):
        with pytest.raises(ValueError):
            _safe_account(bad)


# --- AccountConfig ---


def test_config_first_run_is_empty(tmp_path):
    cfg = AccountConfig.load(tmp_path)
    assert cfg.active is None
    assert cfg.accounts == []


def test_config_use_sets_active_registers_and_persists(tmp_path):
    cfg = AccountConfig.load(tmp_path)
    cfg.use("Red")
    reloaded = AccountConfig.load(tmp_path)
    assert reloaded.active == "Red"
    assert reloaded.accounts == ["Red"]


def test_config_remembers_multiple_accounts(tmp_path):
    cfg = AccountConfig.load(tmp_path)
    cfg.use("Red")
    cfg.use("Blue")
    cfg.use("Red")  # switching back doesn't duplicate
    reloaded = AccountConfig.load(tmp_path)
    assert reloaded.active == "Red"
    assert reloaded.accounts == ["Red", "Blue"]


def test_resolve_active_prefers_override_and_registers_it(tmp_path):
    cfg = AccountConfig.load(tmp_path)
    cfg.use("Red")
    assert cfg.resolve_active("Green") == "Green"  # override wins
    assert AccountConfig.load(tmp_path).active == "Green"


def test_resolve_active_falls_back_to_remembered(tmp_path):
    cfg = AccountConfig.load(tmp_path)
    cfg.use("Red")
    assert cfg.resolve_active() == "Red"


def test_resolve_active_none_on_first_run(tmp_path):
    assert AccountConfig.load(tmp_path).resolve_active() is None


def test_delete_removes_and_repoints_active(tmp_path):
    cfg = AccountConfig.load(tmp_path)
    cfg.use("Red")
    cfg.use("Blue")  # active = Blue
    cfg.delete("Blue")  # deleting the active one -> falls back to a remaining
    reloaded = AccountConfig.load(tmp_path)
    assert reloaded.accounts == ["Red"]
    assert reloaded.active == "Red"


def test_delete_last_account_clears_active(tmp_path):
    cfg = AccountConfig.load(tmp_path)
    cfg.use("Red")
    cfg.delete("Red")
    reloaded = AccountConfig.load(tmp_path)
    assert reloaded.accounts == []
    assert reloaded.active is None


def test_delete_account_data_removes_caught_folder(tmp_path):
    store = CaughtStore.for_account(tmp_path, "Red")
    store.add(1)
    assert store.path.exists()
    delete_account_data(tmp_path, "Red")
    assert not store.path.parent.exists()
    # a fresh store for the same name starts empty again
    assert CaughtStore.for_account(tmp_path, "Red").caught == set()


# --- CaughtStore ---


def test_caught_store_empty_for_new_account(tmp_path):
    store = CaughtStore.for_account(tmp_path, "Red")
    assert store.caught == set()
    assert not store.has(1)


def test_caught_add_persists_and_dedupes(tmp_path):
    store = CaughtStore.for_account(tmp_path, "Red")
    assert store.add(1) is True
    assert store.add(1) is False  # already there -> no change
    assert store.add(16) is True
    reloaded = CaughtStore.for_account(tmp_path, "Red")
    assert reloaded.caught == {1, 16}


def test_caught_is_isolated_per_account(tmp_path):
    CaughtStore.for_account(tmp_path, "Red").add(1)
    CaughtStore.for_account(tmp_path, "Blue").add(16)
    assert CaughtStore.for_account(tmp_path, "Red").caught == {1}
    assert CaughtStore.for_account(tmp_path, "Blue").caught == {16}


def test_caught_file_is_human_readable_sorted(tmp_path):
    store = CaughtStore.for_account(tmp_path, "Red")
    store.add(16)
    store.add(1)
    data = json.loads(store.path.read_text("utf-8"))
    assert data == {"caught": [1, 16]}  # sorted, editable
