//Responsive text settings

//jQuery(".featured-article-header").fitText(2, {minFontSize: '0.875em', maxFontSize: '2.375em'});
//jQuery(".article-thumbnail-header").fitText(2, {minFontSize: '0.875em', maxFontSize: '2.375em'});
//$(".div-link").fitText(0.3);
//jQuery(".article-thumbnail-text").fitText(2, {minFontSize: '0.875em', maxFontSize: '2.375em'});
//$(".article-headling").fitText(2.1);
//jQuery(".article-description").fitText(2, {minFontSize: '0.875em', maxFontSize: '2.375em'});
//jQuery(".article-text").fitText(2, {minFontSize: '0.875em', maxFontSize: '2.375em'});
//jQuery(".company-name").fitText(2, {minFontSize: '0.875em', maxFontSize: '2.375em'});
//jQuery(".article-comments").fitText(2, {minFontSize: '0.875em', maxFontSize: '2.375em'});
//jQuery(".post-date").fitText(2, {minFontSize: '0.875em', maxFontSize: '2.375em'});
//jQuery(".view-count").fitText(2, {minFontSize: '0.875em', maxFontSize: '2.375em'});

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

function add_message(message, type) {}


