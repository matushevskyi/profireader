/**
 * Created by oles on 7/3/17.
 */

set_all_images_galleries = function (url, callback, $container) {


    var prefix = 'data-mce-pr-image-gallery-';


    var get_value_units = function (val) {
        var ret = val.replace(/^\s*/, '').replace(/\s*$/, '');
        var value = ret.replace(/^([+-]?([0-9]*[.])?[0-9]+).*$/, '$1');
        var units = ret.replace(/^[+-]?([0-9]*[.])?[0-9]+/, '');
        return [value, units];
    };

    var normalizeWidthHeight = function ($img, attr_name) {
        var def_value = ((attr_name == 'width') ? '100%' : '50%');
        var ret = $img.attr(prefix + attr_name);
        if (ret === undefined) {
            ret = $img.attr(attr_name);
            ret = (ret === undefined) ? def_value : ret;
        }

        var val_units = get_value_units(ret);
        return val_units[0] + (val_units[1] == '' ? 'px' : val_units[1]);
    };

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

        $img.attr('title', item['title'] + "\n" + item['copyright']);
        $img.css('width', normalizeWidthHeight($img, 'width'));
        var height_val_units = get_value_units(normalizeWidthHeight($img, 'height'));
        $img.css({'height': (height_val_units[1] === '%')?('' + (height_val_units[0] / 100. * $img.width()) + 'px'):
            ('' + height_val_units[0] + height_val_units[1])});

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
