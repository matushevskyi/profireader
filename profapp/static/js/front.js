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

function switch_something(element, url, selector_off, selector_on, replace_key_selector) {
    $ok(url, {'on': $(selector_on, element).is(':visible')?false:true}, function (resp) {
        $(selector_off, element).hide();
        $(selector_on, element).hide();
        (resp && resp['on']) ? $(selector_off, element).show() : $(selector_on, element).show();
        if (replace_key_selector)
            $.each(replace_key_selector, function (key, selector) {
                if (key in resp) {
                    $(selector, element).html(resp[key]);
                }
            })
    })
}
