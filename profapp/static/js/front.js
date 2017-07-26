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
