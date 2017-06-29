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

set_all_images_galleries = function (url, callback, $container) {
    var set_item = function ($img, item) {
        $img.css({backgroundImage: 'url(' + fileUrl(item['file_id']) + ')'});
        $img.attr('title', item['title'] + "\n" + item['copyright']);
    };
    var $cont = $($container ? $container : 'body');
    var callback = callback ? callback : function ($img, gallery_data) {
            $img.data('image_gallery_selected_index', 0);
            $img.data('image_gallery_data', gallery_data);

            set_item($img, gallery_data['items'][0]);

            $img.on('click', function (e) {
                var data = $img.data('image_gallery_data');
                var index = $img.data('image_gallery_selected_index');
                index = index + 1;
                index = (index >= data.items.length ? 0 : index);
                $img.data('image_gallery_selected_index', index);
                set_item($img, gallery_data['items'][index]);
            });
        };

    $('img.data-mce-image-gallery-placeholder', $cont).each(function (ind, img) {
        $ok(url, {'gallery_id': $(img).attr('data-mce-image-gallery-placeholder')}, function (resp) {
            callback($(img), resp);
        });
    });
};

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