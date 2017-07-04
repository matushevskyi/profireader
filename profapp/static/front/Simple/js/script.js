function $ok(url, data, success, fail) {
    $.ajax({
        url: url,
        type: "POST",
        data: JSON.stringify(data),
        contentType: "application/json; charset=utf-8",
        dataType: "json",
        fail: fail ? function (resp) {
                fail(resp);
            } : null,
        success: success ? function (resp) {
                if (resp['ok']) {
                    success(resp['data'])
                }
                else if (fail) {
                    fail(resp['data'])
                }
            } : null
    });
}

function add_message(message, type) {

}

function fileUrl(id, down, if_no_file) {

    if (!id) return (if_no_file ? if_no_file : '');

    if (!id.match(/^[^-]*-[^-]*-4([^-]*)-.*$/, "$1")) return (if_no_file ? if_no_file : '');

    var server = id.replace(/^[^-]*-[^-]*-4([^-]*)-.*$/, "$1");
    if (down) {
        return '//file' + server + '.' + MAIN_DOMAIN + '/' + id + '?d'
    } else {
        return '//file' + server + '.' + MAIN_DOMAIN + '/' + id + '/'
    }
}
