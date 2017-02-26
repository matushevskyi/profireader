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

//Clamp.js settings

/*var paragraph = document.getElementsByClassName("article-thumbnail-text");
$clamp(paragraph, {clamp: 4});*/

//$clamp('article-thumbnail-text', {clamp: 3});



$(window).bind('load', function() {
  // Clamp.js
  $clamp(document.getElementsByClassName("article-thumbnail-text"), {clamp: 3});
  });
