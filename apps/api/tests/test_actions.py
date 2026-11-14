import asyncio

import pytest

from super_agent_voice import actions


def refused(name, arguments):
    with pytest.raises(actions.Refused) as error:
        actions.prepare(name, arguments)
    return str(error.value)


def test_open_url_builds_the_summary_and_command_from_the_parsed_address():
    summary, argv = actions.prepare("open_url", {"url": "https://Example.com/docs/a-b"})
    assert summary == "Open https://example.com/docs/a-b in your browser?"
    assert argv == ["/usr/bin/open", "https://example.com/docs/a-b"]
    assert actions.prepare("open_url", {"url": "https://example.com:443"})[1][1] == "https://example.com/"
    assert actions.prepare("open_url", {"url": "https://a.b.example.org/x"})[0].startswith("Open https://a.b.")


def test_open_url_drops_the_query_and_fragment_because_they_can_carry_data():
    _, argv = actions.prepare("open_url", {"url": "https://example.com/p?leak=my+notes&a=1#more"})
    assert argv[1] == "https://example.com/p"
    assert "leak" not in actions.prepare("open_url", {"url": "https://example.com/p?leak=1"})[0]


@pytest.mark.parametrize("url", [
    "http://example.com/",
    "ftp://example.com/",
    "file:///etc/hosts",
    "javascript:alert(1)",
    "https:example.com",
    "//example.com/",
    "example.com",
    "https://router.lan/admin",
    "https://nas.home.arpa/",
    "https://x.corp/",
    "https://site.test/",
    "https://xn--pple-43d.com/",
    "https://www.xn--pple-43d.com/",
    "https://example.com/" + "a" * 64,
    "https://example.com/%73%65%63%72%65%74",
    "https://example.com/a+b",
    "https://example.com/a;b",
    "https://user:pw@example.com/",
    "https://user@example.com/",
    "https://example.com@evil.com/",
    "https://example.com:8443/",
    "https://example.com:80/",
    "https://example.com:bad/",
    "https:///path",
    "https://localhost/",
    "https://intranet/",
    "https://nas.local/",
    "https://127.0.0.1/",
    "https://127.1/",
    "https://2130706433/",
    "https://0x7f.1/",
    "https://[::1]/",
    "https://[2001:db8::1]/",
    "https://example.com./",
    "https://-bad-.example.com/",
    "https://exa mple.com/",
    "https://example.com/a b",
    "https://example.com/\tx",
    "https://example.com/\nx",
    "https://example.com/​x",
    "https://exаmple.com/",  # Cyrillic a
    "https://example.com\\@evil.com/",
    "https://example.com/" + "a" * 300,
    "",
])
def test_open_url_refuses_unsafe_addresses(url):
    assert refused("open_url", {"url": url}) == actions.BAD_URL


def test_web_search_builds_the_address_in_code():
    summary, argv = actions.prepare("web_search", {"query": "  best   pizza\nin town & more "})
    assert summary == 'Search the web for "best pizza in town & more"?'
    assert argv == ["/usr/bin/open", "https://duckduckgo.com/?q=best+pizza+in+town+%26+more"]
    # Text that would end the query early or add a parameter is encoded, not passed on.
    assert actions.prepare("web_search", {"query": "a&b=c#d"})[1][1] == "https://duckduckgo.com/?q=a%26b%3Dc%23d"


def test_web_search_drops_invisible_characters_and_bounds_length():
    assert actions.prepare("web_search", {"query": "pi​z‮za"})[0] == 'Search the web for "pizza"?'
    assert actions.prepare("web_search", {"query": "x" * 100})[0]
    for query in ("", "   ", "​\n", "x" * 101):
        assert refused("web_search", {"query": query}) == actions.BAD_QUERY


def test_open_app_uses_the_allowlist_spelling_and_nothing_else():
    assert actions.prepare("open_app", {"name": "calendar"}) == ("Open the app Calendar?", ["/usr/bin/open", "-a", "Calendar"])
    assert actions.prepare("open_app", {"name": " SAFARI "})[1] == ["/usr/bin/open", "-a", "Safari"]
    for name in ("Terminal", "Calendar.app", "/Applications/Calendar.app", "Calendar; rm", "-a", "", "Cal"):
        assert refused("open_app", {"name": name}) == actions.BAD_APP


def test_the_app_list_can_be_overridden_and_a_bad_list_fails_closed(monkeypatch):
    monkeypatch.setenv("SUPER_AGENT_ACTION_APPS", "Spotify, Visual Studio Code")
    assert actions.allowed_apps() == ("Spotify", "Visual Studio Code")
    assert actions.prepare("open_app", {"name": "spotify"})[1][-1] == "Spotify"
    assert refused("open_app", {"name": "Calendar"}) == actions.BAD_APP
    for bad in ("Notes,", "Notes,,Maps", "", "Note$", "../Notes", "Notes;Maps", "x" * 41, "Café"):
        monkeypatch.setenv("SUPER_AGENT_ACTION_APPS", bad)
        with pytest.raises(RuntimeError):
            actions.allowed_apps()


@pytest.mark.parametrize("arguments", [
    None, "https://example.com", ["https://example.com"], {}, {"url": 5}, {"url": None}, {"url": ["x"]},
    {"url": "https://example.com", "extra": "x"}, {"link": "https://example.com"}, {"url": "x" * 2001},
    {"url": b"https://example.com"},
])
def test_bad_argument_shapes_are_refused(arguments):
    assert refused("open_url", arguments) == actions.BAD_ARGS


def test_unknown_names_are_refused_and_every_tool_is_declared():
    for name in ("run_shell", "open_file", None, 3, "OPEN_URL"):
        assert refused(name, {"url": "https://example.com"}) == actions.NO_TOOL
    assert actions.NAMES == {"open_url", "web_search", "open_app"}
    for tool in actions.TOOLS:
        assert tool["function"]["parameters"]["required"] == list(tool["function"]["parameters"]["properties"])


def run(coroutine):
    return asyncio.run(asyncio.wait_for(coroutine, timeout=5))


def test_run_executes_only_after_an_explicit_true_and_logs_metadata_only(monkeypatch):
    calls = []

    async def execute(argv):
        calls.append(argv)
    monkeypatch.setattr(actions, "execute", execute)

    def asked(answer):
        async def approve(summary):
            return answer
        return run(actions.run("open_url", {"url": "https://example.com/secret-path?q=hidden"}, approve))

    assert asked(True) == actions.DONE
    assert calls == [["/usr/bin/open", "https://example.com/secret-path"]]
    for answer in (False, None, 1, "yes", [True]):
        assert asked(answer) == actions.DENIED
    assert len(calls) == 1

    async def late(summary):
        raise TimeoutError
    assert run(actions.run("open_url", {"url": "https://example.com"}, late)) == actions.TIMED_OUT
    assert run(actions.run("open_url", {"url": "http://example.com"}, late)) == actions.BAD_URL
    assert run(actions.run("open_url", {"url": "https://example.com"}, None)) == actions.NO_APPROVER
    assert len(calls) == 1
    log = actions.AUDIT_LOG.read_text()
    assert [line.split()[1:] for line in log.splitlines()] == (
        [["open_url", "approved"]] + [["open_url", "denied"]] * 5 + [["open_url", "timeout"],
                                                                      ["open_url", "refused"], ["open_url", "refused"]])
    assert "example" not in log and "secret" not in log and "hidden" not in log
    assert actions.AUDIT_LOG.stat().st_mode & 0o777 == 0o600


def test_a_failed_or_slow_command_gives_a_fixed_error(monkeypatch):
    async def approve(summary):
        return True

    async def broken(argv):
        raise RuntimeError("https://example.com leaked in an exception")

    async def slow(argv):
        raise TimeoutError

    for execute in (broken, slow):
        monkeypatch.setattr(actions, "execute", execute)
        assert run(actions.run("open_url", {"url": "https://example.com"}, approve)) == actions.FAILED
    assert actions.AUDIT_LOG.read_text().count("open_url error") == 2


def test_cancelling_a_waiting_action_is_logged_as_denied(monkeypatch):
    async def execute(argv):
        raise AssertionError("must not run")
    monkeypatch.setattr(actions, "execute", execute)

    async def scenario():
        async def approve(summary):
            await asyncio.sleep(60)
        task = asyncio.create_task(actions.run("open_app", {"name": "Notes"}, approve))
        await asyncio.sleep(0)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    run(scenario())
    assert actions.AUDIT_LOG.read_text().split()[1:] == ["open_app", "denied"]


def test_the_real_executor_uses_an_argument_list_and_reports_failure(monkeypatch):
    seen = {}

    class Process:
        returncode = 1

        async def wait(self):
            return 1

    async def spawn(*argv, **options):
        seen["argv"], seen["options"] = argv, options
        return Process()
    monkeypatch.setattr(asyncio, "create_subprocess_exec", spawn)
    with pytest.raises(RuntimeError):
        run(actions.execute(["/usr/bin/open", "-a", "Notes"]))
    assert seen["argv"] == ("/usr/bin/open", "-a", "Notes")
    assert "shell" not in seen["options"]
    assert {seen["options"][key] for key in ("stdin", "stdout", "stderr")} == {asyncio.subprocess.DEVNULL}


def test_the_card_summary_is_never_longer_than_the_console_shows():
    for url in ("https://" + "a" * 60 + "." + "b" * 60 + ".com/" + "c" * 63, "https://example.com/" + "a" * 63):
        try:
            summary, _ = actions.prepare("open_url", {"url": url})
        except actions.Refused:
            continue
        assert len(summary) <= actions.MAX_SUMMARY
    assert len(actions.prepare("web_search", {"query": "q" * actions.MAX_QUERY})[0]) <= actions.MAX_SUMMARY


def test_the_audit_log_is_tightened_and_never_followed_through_a_link(tmp_path, monkeypatch):
    log = tmp_path / "audit.log"
    log.write_text("")
    log.chmod(0o644)
    monkeypatch.setattr(actions, "AUDIT_LOG", log)
    actions.audit("open_url", "denied")
    assert log.stat().st_mode & 0o777 == 0o600
    target = tmp_path / "elsewhere"
    target.write_text("")
    link = tmp_path / "link.log"
    link.symlink_to(target)
    monkeypatch.setattr(actions, "AUDIT_LOG", link)
    actions.audit("open_url", "denied")
    assert target.read_text() == ""
