tinymce.PluginManager.add('gallery', function (editor, url) {
    // Add a button that opens a window
    editor.addButton('gallery', {
        text: 'Gallery',
        icon: false,
        stateSelector: 'image-gallery:not([data-mce-object],[data-mce-placeholder])',
        onclick: function () {
            var galleryElm = editor.selection.getNode();
            console.log(galleryElm);
            var defaultdata = {width: '400', height: '400', gallery_title: 'Gallery'};
            var data = $.extend({}, defaultdata);
            if (galleryElm && galleryElm.nodeName == 'IMAGE-GALLERY' && !galleryElm.getAttribute('data-mce-object') && !galleryElm.getAttribute('data-mce-placeholder')) {
                data = {
                    width: $(galleryElm).css('width'),
                    height: $(galleryElm).css('height'),
                    gallery_title: $(galleryElm).alt(),
                };
            } else {
                galleryElm = null;
            }

            var win = editor.windowManager.open({
                title: 'Article gallery',
                data: data,
                buttons: [{
                    'classes': 'image-gallery-upload',
                    'text': "Upload", onclick: function () {
                        $('.mce-sortable-images div input[type=file]').trigger('click');
                    }
                },
                    {
                        'text': "Save",
                        'onclick': function () {
                            console.log(win);
                            var normalize_size = function (s, d) {
                                var ret = s.trim();
                                return (ret.match(/^\d+(\.\d*)?(%|)$/) || ret.match(/^(\d*\.)?\d+(%|)$/)) ? ret : d;
                            };

                            var first_image = get_image(0);
                            editor.selection.collapse(true);
                            var new_id = randomHash();
                            console.log(first_image.css('backgroundImage'));
                            editor.execCommand('mceInsertContent', false,
                                '<img id="' + new_id + '" ' +
                                'class="image-gallery-tinymce-preview" ' +
                                'src="' + static_address('images/0.gif') + '" ' +
                                'style="background-image: url(' + first_image.css('backgroundImage') + ')" ' +
                                'width="' + normalize_size(win.data.data.width, defaultdata['width']) + '" ' +
                                'height="' + normalize_size(win.data.data.height, defaultdata['height']) + '" ' +
                                'data-mce-object="gallery"/>');
                            tinymceRenderGalleryPreview(new_id);
                            // editor.dom.createHTML('image-gallery', {
                            //     astyle: 'width: ' + normalize_size(win.data.data.width,
                            //         defaultdata['width']) + '; height: ' + normalize_size(win.data.data.height, defaultdata['height']),
                            // }));
                            win.close();
                        }
                    }, {
                        'text': "Cancel",
                        'onclick': function () {
                            win.close();
                        }
                    }
                ],

                bodyType: 'form',
                body: [{
                    name: 'gallery_title', type: 'textbox', label: 'Gallery Title'
                },
                    {
                        type: 'container',
                        label: 'Dimensions',
                        layout: 'flex',
                        direction: 'row',
                        align: 'center',
                        spacing: 5,
                        items: [
                            {name: 'width', type: 'textbox', size: 3, ariaLabel: 'Width'},
                            {type: 'label', text: 'x'},
                            {name: 'height', type: 'textbox', size: 3, ariaLabel: 'Height'},
                        ]
                    }, {
                        type: 'container',
                        minHeight: 300,
                        minWidth: 500,
                        classes: 'sortable-images'
                    },
                ],
            });

            var get_image_container = function () {
                return images_container = $('#' + win._id + ' ul.ul-sortable-images');
            };

            var get_image = function (n) {
                return $($('img', get_image_container())[n]);
            };


            var add_html = function () {
                var images_container = get_image_container();
                var ret = $('<li mce-container-body mce-abs-layout>' +
                    '<img src="' + static_address('images/0.gif') + '" />' +
                    '<input class="mce-textbox mce-first pr-gallery-image-title" hidefocus="1" style="width: 10em;"/>' +
                    '<input class="mce-textbox" hidefocus="1" style="width: 5em;"/>' +
                    '<div class="mce-btn"><button role="presentation" type="button" tabindex="-1" style="height: 100%; width: 4em;">Remove</button></div>' +
                    '</li>');
                images_container.append(ret);
                images_container.sortable({
                    axis: "y",
                    containment: $('.mce-sortable-images div'),
                    handle: "img"
                });
                images_container.disableSelection();
                return ret;

            }

            var append_image = function (file_title, file_content, file_mime) {
                var container_row = add_html();
                $('img', container_row).css({backgroundImage: 'url(' + file_content + ')'});
                $('.pr-gallery-image-title', container_row).val(file_title);
            };

            $('#' + win._id + ' .mce-sortable-images div').append('<ul class="ul-sortable-images"></ul>');
            $('#' + win._id + ' .mce-sortable-images div').append('<input type="file" multiple />');
            $('#' + win._id + ' .mce-sortable-images div input[type=file]').bind('change', function (event) {
                var the_files = (event.target.files && event.target.files.length) ? event.target.files : [];
                var uploaders = [];

                for (var i = 0; i < the_files.length; i++) {
                    uploaders.push(new FileReader());
                    uploaders[i].onload = (function (the_file, uploader) {
                        return function (e) {
                            var beginstr = uploader.result.substr(0, 50);
                            if (beginstr.match(/^data:image\/(png|gif|jpeg);base64/g)) {
                                append_image(the_file.name, uploader.result, the_files.type);
                            }
                            else {
                                uploader.onerror(e);
                            }
                        }
                    })(the_files[i], uploaders[i]);

                    uploaders[i].onerror = (function (the_file, uploader) {
                        return function (e) {
                            add_message('File loading error: `' + the_file.name + '`', 'warning');
                        }
                    })(the_files[i], uploaders[i]);

                    uploaders[i].readAsDataURL(the_files[i]);
                }
                $(this).val('');
            });
        }
    })
    ;

// Adds a menu item to the tools menu
//  editor.addMenuItem('gallery', {
//    text: 'Example plugin',
//    context: 'tools',
//    onclick: function() {
//      // Open window with a specific url
//      editor.windowManager.open({
//        title: 'TinyMCE site',
//        url: 'http://www.tinymce.com',
//        width: 800,
//        height: 600,
//        buttons: [{
//          text: 'Close',
//          onclick: 'close'
//        }]
//      });
//    }
//  });
})
;