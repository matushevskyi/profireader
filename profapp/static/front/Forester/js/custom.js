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

// jquery.dotdotdot settings

$(document).ready(function() {
	$(".article-thumbnail-text").dotdotdot({
		/*	The text to add as ellipsis. */
		ellipsis	: '... ',

		/*	How to cut off the text/html: 'word'/'letter'/'children' */
		wrap		: 'word',

		/*	Wrap-option fallback to 'letter' for long words */
		fallbackToLetter: true,

		/*	jQuery-selector for the element to keep and put after the ellipsis. */
		after		: null,

		/*	Whether to update the ellipsis: true/'window' */
		watch		: false,

		/*	Optionally set a max-height, can be a number or function.
			If null, the height will be measured. */
		height		: null,

		/*	Deviation for the height-option. */
		tolerance	: 0,

		/*	Callback function that is fired after the ellipsis is added,
			receives two parameters: isTruncated(boolean), orgContent(string). */
		callback	: function( isTruncated, orgContent ) {},

		lastCharacter	: {

			/*	Remove these characters from the end of the truncated text. */
			remove		: [ ' ', ',', ';', '.', '!', '?' ],

			/*	Don't add an ellipsis if this array contains
				the last character of the truncated text. */
			noEllipsis	: []
		}
	});
});