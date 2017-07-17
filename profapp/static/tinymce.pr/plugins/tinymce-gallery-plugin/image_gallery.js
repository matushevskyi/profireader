/**
 * Created by oles on 7/3/17.
 */

set_all_images_galleries = function (url, callback, $container) {

    var set_item = function ($img, item) {
        $img.css({backgroundImage: ''});
        $img.css({backgroundSize: 'auto'});
        // setTimeout(function () {
        var $loader = $('<img>');
        $loader.on('load', function () {
            $img.css({backgroundImage: 'url(' + $loader.attr('src') + ')'});
            $img.css({backgroundSize: 'contain'});
        });
        $loader.attr('src', fileUrl(item['file_id']));
        // }, Math.random()*10000);

        $img.attr('title', item['title'] + "\n" + item['copyright']);
    };
    var $cont = $($container ? $container : 'body');
    var callback = callback ? callback : function ($img, gallery_data) {
            $img.data('image_gallery_selected_index', 0);
            $img.data('image_gallery_data', gallery_data);

            set_item($img, gallery_data['items'][0]);

            if (gallery_data['items'].length > 1) {
                $img.css({cursor: 'pointer'});
                $img.on('click', function (e) {
                    var data = $img.data('image_gallery_data');
                    var index = $img.data('image_gallery_selected_index');
                    index = index + 1;
                    index = (index >= data.items.length ? 0 : index);
                    $img.data('image_gallery_selected_index', index);
                    set_item($img, gallery_data['items'][index]);
                });
            }
        };

    $('img.data-mce-image-gallery-placeholder', $cont).each(function (ind, img) {
        $ok(url, {'gallery_id': $(img).attr('data-mce-image-gallery-placeholder')}, function (resp) {
            callback($(img), resp);
        });
    });
};


$(function () {
    $.each(document.getElementsByTagName('script'), function (ind, script) {
        var url = $(script).attr('data-gallery-load-url');
        if (url) {
            set_all_images_galleries(url);
        }
    });
});
