tinymce.PluginManager.add('gallery', function (editor, url) {
    // Add a button that opens a window
    editor.addButton('gallery', {
        text: 'Gallery',
        icon: false,
        onclick: function () {

            var add_image = function () {
                console.log(win.add({
                    type: 'textbox',
                    name: 'wordcount',
                }));
                console.log(win);
            }

            image_row = {
                type: 'container',
                layout: 'flex',
                name: 'images_container',
                direction: 'row',
                classes: 'sortable-images-row',
                align: 'center',
                spacing: 5,
                items: [
                    {
                        name: 'image_title',
                        type: 'textbox',
                        size: 10,
                        label: 'Title'
                    },
                    {
                        name: 'image_copyright',
                        type: 'textbox',
                        size: 10,
                        label: 'Copyright'
                    },
                    {
                        type: 'filepicker',
                        filetype: 'image',
                        label: 'Source',
                        size: 10,
                    },
                    {
                        type: 'button',
                        label: 'Del',
                        size: 1,

                    },
                ]
            };

            console.log('!!!');
            win = editor.windowManager.open({
                title: 'Article gallery',
                bodyType: 'tabpanel',
                body: [
                    {
                        title: 'General',
                        type: 'form',
                        items: [{
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
                                    {
                                        name: 'width',
                                        type: 'textbox',
                                        maxLength: 5,
                                        size: 3,
                                        ariaLabel: 'Width'
                                    },
                                    {type: 'label', text: 'x'},
                                    {
                                        name: 'height',
                                        type: 'textbox',
                                        maxLength: 5,
                                        size: 3,
                                        ariaLabel: 'Height'
                                    },
                                ]
                            }
                        ]
                    }, {
                        title: 'Images',
                        direction: 'column',
                        layout: 'flex',
                        items: [{
                            type: 'container',
                            minHeight: 300,
                            minWidth: 500,
                            classes: 'sortable-images'
                        }, {
                            type: 'container',
                            direction: 'row',
                            align: 'right',
                            spacing: 5,
                            minHeight: 50,
                            classes: 'sortable-images-controls',
                            minWidth: 500,
                            items: []
                        }],

                    }],
                onsubmit: function (e) {
                    console.log(e.data);
                    console.log(win.toJSON());
                }
            });

            var add_html = function () {
                var images_container = $('#' + win._id + ' ul.ul-sortable-images');
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
            $('#' + win._id + ' .mce-sortable-images-controls div').append('<input class="mce-btn"><input type="file" multiple class="pr-gallery-upload" role="presentation" tabindex="-1" style="height: 100%; width: 100%;"/></div>');
            $('#' + win._id + ' .mce-sortable-images-controls .pr-gallery-upload').bind('change', function (event) {
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

            // <div id="mceu_57-body" class="mce-container-body mce-abs-layout ui-sortable" style="width: 372px; height: 30px;"><div id="mceu_57-absend" class="mce-abs-end ui-sortable"></div><input id="mceu_58" class="mce-textbox mce-abs-layout-item mce-first" value="" hidefocus="1" size="10" style="left: 0px; top: 0px; width: 92px; height: 28px;"><input id="mceu_59" class="mce-textbox mce-abs-layout-item" value="" hidefocus="1" size="10" style="left: 107px; top: 0px; width: 92px; height: 28px;"><div id="mceu_60" class="mce-combobox mce-abs-layout-item mce-has-open ui-sortable" style="left: 214px; top: 0px; width: 135px; height: 30px;"><input id="mceu_60-inp" class="mce-textbox" value="" hidefocus="1" spellcheck="false" size="10" placeholder="" style="width: 92px;"><div id="mceu_60-open" class="mce-btn mce-open ui-sortable" tabindex="-1" role="button"><button id="mceu_60-action" type="button" hidefocus="1" tabindex="-1"><i class="mce-ico mce-i-browse"></i></button></div></div><div id="mceu_61" class="mce-widget mce-btn mce-btn-1 mce-abs-layout-item mce-last ui-sortable" tabindex="-1" aria-labelledby="mceu_61" role="button" style="left: 354px; top: 6px; width: 16px; height: 16px;"><button role="presentation" type="button" tabindex="-1" style="height: 100%; width: 100%;"></button></div></div>

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