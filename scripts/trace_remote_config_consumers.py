"""Read-only, build-guarded evidence for researched Remote Config consumers.

Keys are manually traced findings, not a general ARM64 data-flow analysis.
No archive extraction, device operation or executable modification is performed.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import zipfile

try:
    from scripts.audit_sdk_dependencies import MachO
    from scripts.trace_sdk_lifecycle import (UUID, branch_target, read_vm,
        selector_calls, verify_window, verify_selector_call, verify_import_call)
except ModuleNotFoundError:
    from audit_sdk_dependencies import MachO
    from trace_sdk_lifecycle import (UUID, branch_target, read_vm,
        selector_calls, verify_window, verify_selector_call, verify_import_call)

BRIDGES = {'int': 0x1001E3F40, 'string': 0x1001E3FE4, 'bool': 0x1001E4084}
KEY_LITERALS = {
    0x102563C1A: 'enable_mtx_tile', 0x102563C2A: 'mtx_offer_tile_target_user_level',
    0x102563C95: 'enable_optimized_logic', 0x102563CAC: 'enable_experimental_logic',
    0x102563CC6: 'ios_framerate_cap', 0x102563CD8: 'override_client_unlock_levels',
    0x102563D33: 'omp_unlock_level_override',
    0x102563D83: 'exclusive_series_unlock_level_override',
    0x102563DED: 'race_teams_unlock_level_override',
    0x102563E4B: 'wtt_championship_unlock_level_override',
    0x1025710BD: 'activate_rookie_crash_fix', 0x102592319: 'enable_rookie',
    0x1025C0102: 'enable_dynamic_ads', 0x1025EDEFF: 'enable_custom_logs_for_events',
    0x102602264: 'ad_feature_drive_points_cap', 0x102602280: 'ad_feature_crew_hire_cap',
    0x102602299: 'enable_ad_feature_drive_points',
    0x1026022B8: 'ad_feature_crew_hire_min_level',
    0x1026022D7: 'ad_feature_crew_hire_max_level',
    0x1026022F6: 'enable_ad_feature_crew_hire',
}
# Exact call-site -> (type, key) reviewed against the guarded instruction windows.
CONSUMERS = {
    0x100079D64: ('bool', 'enable_mtx_tile'),
    0x100079DBC: ('int', 'mtx_offer_tile_target_user_level'),
    0x100079E04: ('string', 'ABTestId'),
    0x100079E78: ('string', 'CohortId'),
    0x100079FCC: ('bool', 'enable_optimized_logic'),
    0x10007A028: ('bool', 'enable_experimental_logic'),
    0x10007A070: ('int', 'ios_framerate_cap'),
    0x10007A0E0: ('bool', 'override_client_unlock_levels'),
    0x10007A158: ('int', 'omp_unlock_level_override'),
    0x10007A1C0: ('int', 'exclusive_series_unlock_level_override'),
    0x10007A218: ('int', 'race_teams_unlock_level_override'),
    0x10007A278: ('int', 'wtt_championship_unlock_level_override'),
    0x10007A2AC: ('string', 'ABTestId'),
    0x10007A2F8: ('string', 'CohortId'),
    0x100139D40: ('bool', 'activate_rookie_crash_fix'),
    0x1003C6EB0: ('bool', 'enable_rookie'),
    0x1003C6EF0: ('string', 'ABTestId'),
    0x1003C6F28: ('string', 'CohortId'),
    0x1003C9420: ('bool', 'activate_rookie_crash_fix'),
    0x1006CE574: ('bool', 'enable_dynamic_ads'),
    0x10073A9F0: ('bool', 'enable_mtx_tile'),
    0x100A2432C: ('bool', 'enable_custom_logs_for_events'),
    0x100AB05B4: ('bool', 'override_client_unlock_levels'),
    0x100AB0600: ('int', 'wtt_championship_unlock_level_override'),
    0x100B48270: ('int', 'ad_feature_drive_points_cap'),
    0x100B482DC: ('int', 'ad_feature_crew_hire_cap'),
    0x100B4837C: ('int', 'ad_feature_drive_points_cap'),
    0x100B483EC: ('int', 'ad_feature_crew_hire_cap'),
    0x100B4909C: ('bool', 'enable_ad_feature_drive_points'),
    0x100B49114: ('int', 'ad_feature_crew_hire_min_level'),
    0x100B49174: ('int', 'ad_feature_crew_hire_max_level'),
    0x100B49228: ('bool', 'enable_ad_feature_crew_hire'),
}
WINDOWS = {
    'game_config_population': (0x100079d0c, 0xb5c, '8ad2f4461534e6f236bce7e07b34ab91d5697706f53f03139db13f32c209d6ca'),
    'bridge_int': (0x1001e3f40, 0xa4, 'e27e211be7e052daf4413e0ee7cc3b85bd92a784699850649c6e912d673c5353'),
    'bridge_string': (0x1001e3fe4, 0xa0, '7750fa9989d772104772a5f1d9f375fa9882ee75e09defc7a0fdb3ad26db810f'),
    'bridge_bool': (0x1001e4084, 0xa4, '927f185750ba2f3cf65f77c6722c67976ef51d68b6c2c07d9636fa9fff0958fd'),
    'objc_getters': (0x100820128, 0x16c, 'c3b9416b22398c098d06257805458177b9476ada5adfc792e35ed07674e8acf5'),
    'rookie_init': (0x1003c6e88, 0xa8, 'bc512fffc4fb0a3edb7ee3bfb0ad7810f613d824bf222d78179391ea732bca52'),
    'framerate': (0x10007a048, 0x60, '154aee6b1129cc9ae1b1f55e5651a98cb2e01125d2c408ff67a3911de4617da4'),
    'unlock_fallback': (0x100ab056c, 0x150, 'e05ec7d79cfc53afa73e6ddec97ad454336f8a8fcb727a3e58232c4dfb7c4936'),
    'reward_caps': (0x100b48204, 0x214, 'fa3ab903814fea363322964202730fa16ea3705409532e1a822d8fd53d81d9e4'),
    'reward_eligibility': (0x100b49040, 0x1fc, '7481e682dfd0a66f2d2360365036e7c83ca0e99a6e498cf0a893150e935e5943'),
    'active_default_getter': (0x101edab44, 0x3a8, '3ee3e0ea5e531a8dce096202e0bbd2e6d7cecf16a27d98d5f60c6de984cd119f'),
    'value_conversions': (0x101ed9064, 0x160, 'bc825b2695b2c0505dfce864d6e00697d4c757ad2dcdb66cceed62adfc9b2425'),
    'default_setter': (0x101edb970, 0x1f0, '24f53b8419af9f780960cd924dda959114a8d41d62778ce07193845d1a5d8ec0'),
    'content_init': (0x101edd358, 0x1dc, '1c38aaafbcfe8e38872388a4c6aa9b7422fb5e9d7701807a05240d2009301cbb'),
    'db_callback': (0x101edd5ec, 0x14c, '40bcaabbb416945e0242653baea383b1ee62468c1a325f6010a11219319a733d'),
    'content_getters': (0x101ede598, 0x6c, 'cb84aba482025f447ea279e3fb1b43385bb27374f5e60752d36565eb4627f90d'),
    'db_wait': (0x101ede728, 0x84, 'ff03881c5c4a26d3c8e6bfcbf1d36a48de0f822117b0712e4882c4ccc3cbddc0'),
    'activation': (0x101eda3e4, 0xb0, 'bb935c01288634b740327cfea8b334fdd5ab0196b7aea37531f4a8140557a22c'),
}


def direct_calls(image, targets):
    """Scan aligned B/BL in __text only; indirect/script calls are not counted."""
    result = {}
    for section in image.sections:
        if section['name'] != '__text':
            continue
        data = read_vm(image, section['address'], section['size'])
        for offset in range(0, len(data) - 3, 4):
            address = section['address'] + offset
            target = branch_target(struct.unpack_from('<I', data, offset)[0], address)
            if target in targets:
                result[address] = target
    return result


def trace_image(image):
    if image.uuid != UUID:
        raise ValueError('Unsupported executable UUID')
    guards = {name: verify_window(image, *window) for name, window in WINDOWS.items()}
    for address, key in KEY_LITERALS.items():
        if image.vm_string(address) != key:
            raise ValueError('Changed key literal at ' + hex(address))
    calls = direct_calls(image, set(BRIDGES.values()))
    expected = {address: BRIDGES[kind] for address, (kind, _) in CONSUMERS.items()}
    if calls != expected:
        raise ValueError('Typed bridge direct-call coverage changed')
    # Selected caller windows not already covered by the larger semantic windows.
    for address, digest in CALLER_GUARDS.items():
        guards[hex(address)] = verify_window(image, address - 0x40, 0x64, digest)
    selected = [verify_selector_call(image, address, selector) for address, selector in (
        (0x101EDADD0, 'activeConfig'), (0x101EDAEB8, 'defaultValueForFullyQualifiedNamespace:key:'),
        (0x101EDAB78, 'defaultConfig'), (0x101EDD510, 'loadConfigFromMainTable'),
        (0x101EDD5A4, 'loadMainWithBundleIdentifier:completionHandler:'),
        (0x101EDE5CC, 'checkAndWaitForInitialDatabaseLoad'),
        (0x101EDE5F0, 'checkAndWaitForInitialDatabaseLoad'),
        (0x101EDA460, 'fetchedConfig'), (0x101EDA484, 'copyFromDictionary:toSource:forNamespace:'),
        (0x101EDBAF4, 'copyFromDictionary:toSource:forNamespace:'),
        (0x1009313C8, 'setFramerateCapEnabled:'))]
    imports = [verify_import_call(image, address, symbol) for address, symbol in (
        (0x101EDACF8, '_dispatch_sync'), (0x101EDE75C, '_dispatch_time'),
        (0x101EDE768, '_dispatch_group_wait'), (0x101EDD734, '_dispatch_group_leave'))]
    setters = selector_calls(image, {'setDefaults:', 'setDefaultsFromPlistFileName:', 'activateWithCompletion:'})
    expected_setters = {'setDefaults:': [0x101EDBF50], 'setDefaultsFromPlistFileName:': [],
                        'activateWithCompletion:': [0x101EDA180]}
    if {name: [x['address'] for x in found] for name, found in setters.items()} != expected_setters:
        raise ValueError('Default/activation direct-selector coverage changed')
    # MOVZ/MOVK sequence feeding dispatch_time: decode its exact guarded constants.
    words = struct.unpack('<III', read_vm(image, 0x101EDE750, 12))
    delta_ns = sum(((word >> 5) & 0xffff) << (((word >> 21) & 3) * 16) for word in words)
    if delta_ns != 30_000_000_000:
        raise ValueError('Changed nominal database initialization timeout')
    return {
        'executable_uuid': image.uuid, 'verified_windows': guards,
        'direct_bridge_call_count': len(calls), 'distinct_keys': len({key for _, key in CONSUMERS.values()}),
        'consumers': [{'call': hex(address), 'type': kind, 'key': key}
                      for address, (kind, key) in CONSUMERS.items()],
        'verified_selector_calls': selected, 'verified_import_calls': imports,
        'default_activation_selector_calls': {name: [hex(x['address']) for x in found]
                                               for name, found in setters.items()},
        'nominal_initial_database_wait_seconds': delta_ns / 1_000_000_000,
        'status': 'no justified suppression patch; gameplay consumers and persistent state matter',
        'limits': ['Key mappings are manually traced findings accepted only for guarded bytes.',
                   'Direct B/BL and selector scans do not enumerate dynamic Objective-C or script dispatch.',
                   'No live database contents, backend values, device latency or gameplay were measured.',
                   'The nominal DB wait is separate from the network fetch timeout; suppression leaves it intact.'],
    }


# Filled with hashes of the reviewed original instruction windows below.
CALLER_GUARDS = {
    0x100079d64: '57bb6d86ce7b51779797e006ff7ad6537755cb51144280a4483c609d0fc97a21',
    0x100079dbc: '5aee04899bc397dc3a99e20a5143273b9afb3f40657c4bef1be54bf7c125a30b',
    0x100079e04: '5f261f144e791adfcd5eb12fadb4138441e7a54d69bfcfa2153aa958324d2ba9',
    0x100079e78: 'b4d79506ebe1d13d5ffdf4d2d625bfaf59b6d31480d23ac7c33e4c99953b13cc',
    0x100079fcc: 'e908e9a9cdab89e4cb054e1e417a9fe8f9bb7038786db997f3288f6480d25793',
    0x10007a028: '53488768990e540d8ee44cb2a4dbbceadf6bd007531162a12ca609c7ae40aae3',
    0x10007a070: 'e890c45f6353823369cf28a9c1dfd60461e80da27a469d9b5b4c32e3348e56cc',
    0x10007a0e0: '951b00865aeb22cc40abda95619dc828fa0c2f236311413d714d8acb1ad85a29',
    0x10007a158: '79440705f26d6ec6e5f5a5909ed46f56f12ed3663bacf4edbdd5d8c2bf3dcd3d',
    0x10007a1c0: 'fb789f46321c1cfef2b4f1879731a0a6f858361f48d57f5fc8ca6a9712a8d721',
    0x10007a218: 'e8b18f553394b3d1058842b89adb1dd3e3c4d37737941f6194bcc22b0cb3da7f',
    0x10007a278: 'c22fe12b93729919acdf46a72326b22d90650a380df2807b8743f6016c312254',
    0x10007a2ac: '2bdda31fed07a04ef381dd34e94d02e84d1138c09289f9b98494988d74ca267b',
    0x10007a2f8: '5bc441452388682b474619729b8870d4c48f9f86e0eb6afe395483f9a51d1912',
    0x100139d40: '504bda189b5ecce00d12c2964bb0ca023036cd67d27d5f3de861d484e2c04e05',
    0x1003c6eb0: '65e24b92ada1dec49443fde80c2985fc5ec47e468eb138acf979640fd6e3d212',
    0x1003c6ef0: '924a9cadb5fc664862fb4ab39189f77413917514384c0c40e47039264a618bbe',
    0x1003c6f28: 'ceb9973ba05f3c88bed47dec82400d6e864d7e221fc6a3b88b209c865026ec15',
    0x1003c9420: '856eb9e2c1397e0c0da874a55e4d57f1a039e6473dfb7cb85d7b91f1fd1b1951',
    0x1006ce574: 'd3b837f3aad87ad1386a2eb5502fbe32be26dd41d762be9a70cb09aa5698767a',
    0x10073a9f0: 'bcf6652a683114c2a1a3c237f8b1859d6d701d52d49f4f3db5aa202e7f4fe1ef',
    0x100a2432c: '375af10e667152ec5dc3f0cef894e6708b3651c1440ee7fca6ab6114c88e9909',
    0x100ab05b4: '94e7edba64428c2a9a1e412d103b9e96f72d9d2aae92d588dea447c2577ec49a',
    0x100ab0600: 'a48372959d8d605b9465784664cb832ddf30d8ccea75254d24d2c7eabd317904',
    0x100b48270: '2cd23db627abc21a25e60b114e84bd2b1e0b6186ac0c1bc7607d7e9c5d4db662',
    0x100b482dc: 'b0c948d433533976a81f018313e0f86724e651e1f5ab468232e5546b8b5071de',
    0x100b4837c: 'c7cddd39d7034264f4af7417e5125458c3a164a3d27f9a448396c4b02d6c298f',
    0x100b483ec: '7147ced460cdf1256f3325324a3ac7167840ea820e5d15fd903692cd129ac0cf',
    0x100b4909c: 'aa7f8d3d7ff8ec2a1fd8e7cb0da26a37efdab35450855e2bbfdcab1b035cb819',
    0x100b49114: '3727a02a94ace42efe14dd2cc105c8fef585e1ec724c126c8eab9936791bcac7',
    0x100b49174: '156902dcf638bc44d65a4e3a7be8e0218ae1ead71b069a88bb92799468697782',
    0x100b49228: 'cbf7e4b1326d14f669dab99259cb78e98b92770ff7b603b1dfdd1b1a20e78472',
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('ipa', type=Path)
    parser.add_argument('--output', type=Path, help='Optional new JSON report; never overwrite')
    args = parser.parse_args()
    if args.output and args.output.resolve() == args.ipa.resolve():
        parser.error('Report must not overwrite the IPA')
    with zipfile.ZipFile(args.ipa) as archive:
        report = trace_image(MachO(archive.read('Payload/RealRacing3.app/RealRacing3')))
    with args.ipa.open('rb') as stream:
        report['input_sha256'] = hashlib.file_digest(stream, 'sha256').hexdigest()
    rendered = json.dumps(report, indent=2) + '\n'
    if args.output:
        with args.output.open('x', encoding='utf-8') as stream:
            stream.write(rendered)
    else:
        print(rendered, end='')


if __name__ == '__main__':
    main()
