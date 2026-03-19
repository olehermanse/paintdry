"""Test that all modules can be imported and their example data constructed."""

from paintdry.lib import ModuleRequest


def _convert_examples(mod):
    requests = mod.example_requests()
    for request in requests:
        ModuleRequest.convert(request)


def test_modlib():
    import modlib

    _convert_examples(modlib.ModBase())


def test_modexample():
    import modexample

    _convert_examples(modexample.ModExample())


def test_moddns():
    import moddns

    _convert_examples(moddns.ModDNS())


def test_modhttp():
    import modhttp

    _convert_examples(modhttp.ModHTTP())


def test_modtls():
    import modtls

    _convert_examples(modtls.ModTLS())


def test_modgithub():
    import modgithub

    _convert_examples(modgithub.ModGitHub())


def test_modcontainers():
    import modcontainers

    _convert_examples(modcontainers.ModContainers())


def test_modsimplechecksums():
    import modsimplechecksums

    _convert_examples(modsimplechecksums.ModSimpleChecksums())


def test_modcfechecksums():
    import modcfechecksums

    _convert_examples(modcfechecksums.ModCFEChecksums())
