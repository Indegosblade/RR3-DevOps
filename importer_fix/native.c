/* RR3 DevOps repair glue for the inherited AppData importer.
 * The upstream UI, ZIP implementation and exporter remain upstream work.
 * No SDK headers: all calls go through the guarded original image's stubs.
 */
typedef __UINTPTR_TYPE__ UP;
typedef __SIZE_TYPE__ SZ;
typedef __UINT64_TYPE__ U64;
typedef __UINT32_TYPE__ U32;
typedef void *ID;
enum {
    TEMP, ALLOC, RELEASE, OPEN, READ, CLOSE, CRC, SYMBOL,
    ZIP_OPEN, ZIP_FIRST, ZIP_INFO, ZIP_MEMBER_OPEN, ZIP_READ,
    ZIP_MEMBER_CLOSE, ZIP_NEXT, ZIP_CLOSE,
    UTF8, STRING_UTF8, APPEND, DEFAULT_MANAGER, EXISTS, MKDIR, COPY,
    REMOVE, EXTRACT, STRING_CLASS, FILE_MANAGER_CLASS, AUTH, API_COUNT
};
#define F(key, type) ((type)(base + api[key]))
#define LIMIT_FILES 64
#define LIMIT_MEMBER (64ULL * 1024 * 1024)
#define LIMIT_TOTAL (256ULL * 1024 * 1024)
#define BUFFER_SIZE 32768

/* dlsym function pointers use the arm64e function-pointer ABI. The raw
 * branch path is used on ordinary arm64; BRAAZ authenticates arm64e pointers.
 * Internal stub addresses are ordinary direct code addresses in either slice.
 */
#if defined(__aarch64__)
#if defined(__APPLE__)
__asm__(".text\n.private_extern _rr3_call2\n.p2align 2\n_rr3_call2:\n"
        "mov x16, x0\nmov x0, x1\nmov x1, x2\ncbz w3, 1f\n"
        ".inst 0xd61f0a1f\n1: br x16\n");
#else
__asm__(".text\n.hidden rr3_call2\n.globl rr3_call2\n.p2align 2\nrr3_call2:\n"
        "mov x16, x0\nmov x0, x1\nmov x1, x2\ncbz w3, 1f\n"
        ".inst 0xd61f0a1f\n1: br x16\n");
#endif
__attribute__((visibility("hidden"))) int rr3_call2(void *, UP, UP, unsigned);
#else
static int rr3_call2(void *fn, UP a, UP b, unsigned auth) {
    (void)auth;
    return ((int (*)(UP, UP))fn)(a, b);
}
#endif

struct Item {
    char name[129];
    U64 size;
    U32 crc;
    ID staged, target, backup;
    int existed, committed;
};

static int same(const char *a, const char *b) {
    for (;;) {
        unsigned x = (unsigned char)*a++, y = (unsigned char)*b++;
        if (x >= 'A' && x <= 'Z') x += 'a' - 'A';
        if (y >= 'A' && y <= 'Z') y += 'a' - 'A';
        if (x != y) return 0;
        if (!x) return 1;
    }
}

static int exact(const char *a, const char *b) {
    while (*a == *b) {
        if (!*a) return 1;
        ++a; ++b;
    }
    return 0;
}

static int metadata(const char *s) {
    const char *prefix = "__MACOSX/";
    int i;
    for (i = 0; prefix[i] && s[i] == prefix[i]; ++i) {}
    return !prefix[i] || same(s, ".DS_Store");
}

static unsigned valid_name(const char *s) {
    unsigned i;
    if (!s[0] || s[0] == '.') return 0;
    for (i = 0; i < 129 && s[i]; ++i) {
        unsigned c = (unsigned char)s[i];
        if (!((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z') ||
              (c >= '0' && c <= '9') || c == '.' || c == '_' || c == '-')) return 0;
    }
    if (i < 5 || i > 128 || s[i]) return 0;
    return s[i-4] == '.' && s[i-3] == 'd' && s[i-2] == 'a' && s[i-1] == 't' ? i : 0;
}

static const char *text(ID s, const UP *api, UP base) {
    return F(UTF8, const char *(*)(ID, ID))(s, 0);
}
static ID string(const char *s, const UP *api, UP base) {
    ID cls = *(ID *)(base + api[STRING_CLASS]);
    return F(STRING_UTF8, ID (*)(ID, ID, const char *))(cls, 0, s);
}
static ID append(ID parent, ID name, const UP *api, UP base) {
    return F(APPEND, ID (*)(ID, ID, ID))(parent, 0, name);
}
static int exists(ID fm, ID path, const UP *api, UP base) {
    return F(EXISTS, unsigned char (*)(ID, ID, ID))(fm, 0, path) != 0;
}
static int remove_path(ID fm, ID path, const UP *api, UP base) {
    return F(REMOVE, unsigned char (*)(ID, ID, ID, ID))(fm, 0, path, 0) != 0;
}
static int mkdir(ID fm, ID path, const UP *api, UP base) {
    return F(MKDIR, unsigned char (*)(ID, ID, ID, unsigned char, ID, ID))(fm, 0, path, 1, 0, 0) != 0;
}

static int check_file(ID path, struct Item *item, void *buffer, const UP *api, UP base) {
    void *file = F(OPEN, void *(*)(const char *, const char *))(text(path, api, base), "rb");
    U64 size = 0;
    U32 crc = 0;
    SZ amount;
    int good;
    if (!file) return 0;
    while ((amount = F(READ, SZ (*)(void *, SZ, SZ, void *))(buffer, 1, BUFFER_SIZE, file))) {
        size += amount;
        if (size > item->size) break;
        crc = (U32)F(CRC, UP (*)(UP, const void *, unsigned))(crc, buffer, (unsigned)amount);
    }
    good = size == item->size && crc == item->crc;
    if (F(CLOSE, int (*)(void *))(file) != 0) good = 0;
    return good;
}

/* Failure returns zero to the original English failure UI. Success terminates
 * this old runtime before its main-thread autosave can overwrite the import.
 * The replacement worker is dispatched on the main queue by the patcher.
 */
#if defined(RR3_TESTING) && defined(_WIN32)
__declspec(dllexport)
#elif defined(RR3_TESTING)
__attribute__((visibility("default"), used))
#else
__attribute__((visibility("hidden"), used))
#endif
int rr3_apply_save(void *captured_block, const UP *api, UP base) {
    ID *block = (ID *)captured_block;
    ID plugin = block[4], source = block[5], destination = block[6];
    struct Item *items = 0;
    void *buffer = 0, *zip = 0, *rename_fn, *exit_fn;
    ID fm, stage = 0, backup_dir;
    unsigned count = 0, visited = 0, i, j, n;
    U64 total = 0;
    int result, found_character = 0, owned_stage = 0, rollback_ok = 1;
    char name[512], stage_name[48];
    const char *hex = "0123456789abcdef";
    void *(*resolve)(void *, const char *) = F(SYMBOL, void *(*)(void *, const char *));
    rename_fn = resolve((void *)(UP)-2, "rename");
    exit_fn = resolve((void *)(UP)-2, "_exit");
    if (!rename_fn || !exit_fn) return 0;
    buffer = F(ALLOC, void *(*)(SZ))(BUFFER_SIZE);
    items = F(ALLOC, void *(*)(SZ))(sizeof(struct Item) * LIMIT_FILES);
    if (!buffer || !items) goto finish;
    zip = F(ZIP_OPEN, void *(*)(const char *))(text(source, api, base));
    if (!zip) goto finish;
    result = F(ZIP_FIRST, int (*)(void *))(zip);
    while (result == 0 && ++visited <= 4096) {
        for (i = 0; i < sizeof(name); ++i) name[i] = 127;
        if (F(ZIP_INFO, int (*)(void *, void *, char *, UP, void *, UP, void *, UP))
                (zip, 0, name, sizeof(name)-1, 0, 0, 0, 0) != 0) goto finish;
        for (n = 0; n < sizeof(name) && name[n]; ++n) {}
        if (n >= sizeof(name)-1) goto finish;
        for (i = n+1; i < sizeof(name); ++i) if (name[i] != 127) goto finish;
        if (!metadata(name)) {
            if (count == LIMIT_FILES || !valid_name(name)) goto finish;
            for (j = 0; j < count; ++j) if (same(items[j].name, name)) goto finish;
            for (i = 0; i <= n; ++i) items[count].name[i] = name[i];
            items[count].size = 0;
            items[count].crc = 0;
            items[count].existed = items[count].committed = 0;
            if (F(ZIP_MEMBER_OPEN, int (*)(void *))(zip) != 0) goto finish;
            while ((result = F(ZIP_READ, int (*)(void *, void *, unsigned))(zip, buffer, BUFFER_SIZE)) > 0) {
                items[count].size += (unsigned)result;
                total += (unsigned)result;
                if (items[count].size > LIMIT_MEMBER || total > LIMIT_TOTAL) { result = -1; break; }
                items[count].crc = (U32)F(CRC, UP (*)(UP, const void *, unsigned))
                    (items[count].crc, buffer, (unsigned)result);
            }
            if (F(ZIP_MEMBER_CLOSE, int (*)(void *))(zip) != 0 || result != 0) goto finish;
            if (exact(name, "character.2.dat")) {
                if (!items[count].size) goto finish;
                found_character = 1;
            }
            ++count;
        }
        result = F(ZIP_NEXT, int (*)(void *))(zip);
    }
    if (result != -100 || !found_character || !count) goto finish;
    if (F(ZIP_CLOSE, int (*)(void *))(zip) != 0) { zip = 0; goto finish; }
    zip = 0;
    fm = F(DEFAULT_MANAGER, ID (*)(ID, ID))(*(ID *)(base + api[FILE_MANAGER_CLASS]), 0);
    if (!fm) goto finish;
    {
        const char *prefix = "rr3-save-stage-";
        for (i = 0; prefix[i]; ++i) stage_name[i] = prefix[i];
        for (j = 0; j < sizeof(UP)*2; ++j) stage_name[i+j] = hex[((UP)buffer >> ((sizeof(UP)*2-1-j)*4)) & 15];
        stage_name[i+j] = 0;
    }
    stage = append(F(TEMP, ID (*)(void))(), string(stage_name, api, base), api, base);
    if (!stage || exists(fm, stage, api, base) || !mkdir(fm, stage, api, base)) goto finish;
    owned_stage = 1;
    if (!F(EXTRACT, unsigned char (*)(ID, ID, ID, ID, ID))(plugin, 0, source, stage, 0)) goto finish;
    for (i = 0; i < count; ++i) {
        ID filename = string(items[i].name, api, base);
        items[i].staged = append(stage, filename, api, base);
        items[i].target = append(destination, filename, api, base);
        if (!check_file(items[i].staged, &items[i], buffer, api, base)) goto finish;
    }
    backup_dir = append(stage, string(".backup", api, base), api, base);
    if (!mkdir(fm, backup_dir, api, base)) goto finish;
    for (i = 0; i < count; ++i) {
        items[i].backup = append(backup_dir, string(items[i].name, api, base), api, base);
        items[i].existed = exists(fm, items[i].target, api, base);
        if (items[i].existed && !F(COPY, unsigned char (*)(ID, ID, ID, ID, ID))
                (fm, 0, items[i].target, items[i].backup, 0)) goto finish;
    }
    for (i = 0; i < count; ++i) {
        if (rr3_call2(rename_fn, (UP)text(items[i].staged, api, base),
                      (UP)text(items[i].target, api, base), (unsigned)api[AUTH]) != 0) goto rollback;
        items[i].committed = 1;
    }
    for (i = 0; i < count; ++i) if (!check_file(items[i].target, &items[i], buffer, api, base)) goto rollback;
    remove_path(fm, stage, api, base);
    if (((unsigned char *)captured_block)[0x41]) remove_path(fm, source, api, base);
    F(RELEASE, void (*)(void *))(items);
    F(RELEASE, void (*)(void *))(buffer);
    rr3_call2(exit_fn, 0, 0, (unsigned)api[AUTH]);
#ifdef RR3_TESTING
    return 1;
#else
    __builtin_trap(); /* _exit must not return into the old runtime. */
#endif
rollback:
    for (i = 0; i < count; ++i) if (items[i].committed) {
        if (items[i].existed) {
            if (rr3_call2(rename_fn, (UP)text(items[i].backup, api, base),
                         (UP)text(items[i].target, api, base), (unsigned)api[AUTH]) != 0) rollback_ok = 0;
        } else if (!remove_path(fm, items[i].target, api, base)) rollback_ok = 0;
    }
finish:
    if (zip) F(ZIP_CLOSE, int (*)(void *))(zip);
    if (owned_stage && rollback_ok) remove_path(fm, stage, api, base);
    /* If rollback itself fails, preserve the owned stage and its backups. */
    if (items) F(RELEASE, void (*)(void *))(items);
    if (buffer) F(RELEASE, void (*)(void *))(buffer);
    return 0;
}
