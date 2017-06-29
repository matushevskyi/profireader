//jQuery to collapse the navbar on scroll
$(window).scroll(function () {
    if ($(".navbar").offset().top > 120) {
        $('nav.navbar-fixed-top').addClass("top-nav-collapse");

        //{#        $(".social-block").addClass("top-nav-collapse");#}
        //{#        $(".navbar").addClass("top-nav-collapse");#}


    } else {
        //{#        $(".social-block").removeClass("top-nav-collapse");#}
        $("nav.navbar-fixed-top").removeClass("top-nav-collapse");
    }
});

//jQuery for page scrolling feature - requires jQuery Easing plugin
$(function () {
    $('a.page-scroll').bind('click', function (event) {
        var $anchor = $(this);
        $('html, body').stop().animate({
            scrollTop: $($anchor.attr('href')).offset().top
        }, 1500, 'easeInOutExpo');
        event.preventDefault();
    });
});

function $ok(url, data, success, fail, progress) {
    $.ajax({

//        xhr: function () {
//            var xhr = new window.XMLHttpRequest();
//            //Upload progress
//            xhr.upload.addEventListener("progress", function (evt) {
//                if (evt.lengthComputable) {
//                    var percentComplete = evt.loaded / evt.total;
//                    //Do something with upload progress
//                    console.log(percentComplete);
//                }
//            }, false);
//            //Download progress
//            xhr.addEventListener("progress", function (evt) {
//                if (evt.lengthComputable) {
//                    var percentComplete = evt.loaded / evt.total;
//                    //Do something with download progress
//                    console.log(percentComplete);
//                }
//            }, false);
//            return xhr;
//        },

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
                    fail(resp)
                }
            } : null
    });
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
