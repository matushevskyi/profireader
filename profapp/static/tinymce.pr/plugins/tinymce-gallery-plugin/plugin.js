tinymce.PluginManager.add('gallery', function (editor, url) {
    // Add a button that opens a window

    // editor.on('NodeChange', function(e) {
    //         console.log('NodeChange', e.element.nodeName );
    // if (e.selectionChange && e.element.nodeName == 'IMAGE-GALLERY-IMG'  || e.element.nodeName == 'IMAGE-GALLERY-TITLE') {
    //     var galleryelem = editor.dom.getParent(editor.selection.getNode(), 'IMAGE-GALLERY');
    //     var selection = editor.selection;
    //     select(node:Element);
    //     selection.select(galleryelem, true);
    //     editor.nodeChanged();
    //     selection.collapse(true);
    // }
    // });


    var dialog_controller = {

        init: function (win_id) {
            $('#' + win_id + ' .mce-sortable-images div').append('<ul class="ul-sortable-images"></ul>');
            $('#' + win_id + ' .mce-sortable-images div').append('<input type="file" multiple />');
            $('#' + win_id + ' .mce-sortable-images div input[type=file]').bind('change', this.upload_images);
            $('#' + win_id + ' .mce-sortable-images').on('click', '.pr-gallery-image-remove-undo', this.remove_undo);
        },

        get_image_container: function () {
            return $('#' + win._id + ' ul.ul-sortable-images');
        },

        upload_images: function (event) {
            var the_files = (event.target.files && event.target.files.length) ? event.target.files : [];
            var uploaders = [];

            for (var i = 0; i < the_files.length; i++) {
                uploaders.push(new FileReader());
                uploaders[i].onload = (function (the_file, uploader) {
                    return function (e) {
                        var beginstr = uploader.result.substr(0, 50);
                        if (beginstr.match(/^data:image\/(png|gif|jpeg);base64/g)) {
                            this.append_image(the_file.name, uploader.result, the_files.type);
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
        },
        remove_undo: function (event) {
            var $li = $(event.currentTarget).closest('li');
            var is_disabled = $('input.pr-gallery-image-title', $li).is(':disabled');
            $('input', $li).prop('disabled', is_disabled ? false : true);
            is_disabled ? $('input,img', $li).removeClass('disabled') : $('input,img', $li).addClass('disabled');
            $('.pr-gallery-image-remove-undo', $li).html(is_disabled ? 'Remove' : 'Undo');
            event.preventDefault();
        },

        add_html: function () {
            var images_container = this.get_image_container();
            var ret = $('<li>' +
                '<img class="pr-gallery-image-preview" src="' + static_address('images/0.gif') + '" />' +
                '<input class="pr-gallery-image-id" hidefocus="1" type="hidden"/>' +
                '<input class="mce-textbox mce-first pr-gallery-image-title" hidefocus="1" placeholder="title"/>' +
                '<input class="mce-textbox pr-gallery-image-copyright" hidefocus="1" placeholder="copyright"/>' +
                '<div class="mce-btn"><button role="presentation" type="button" tabindex="-1" class="pr-gallery-image-remove-undo">Remove</button></div>' +
                '</li>');
            images_container.append(ret);
            images_container.sortable({
                axis: "y",
                containment: $('.mce-sortable-images div'),
                handle: "img"
            });
            images_container.disableSelection();
            return ret;

        },

        append_image: function (file_title, file_content, file_mime) {
            var container_row = this.add_html();
            $('img', container_row).css({backgroundImage: 'url(' + file_content + ')'});
            $('.pr-gallery-image-title', container_row).val(file_title);
        }
    };

    var editor_controller = {

        getSheet: function () {
            // Create the <style> tag
            var iframe_content = $(editor.iframeElement).contents()[0];


            var csssheet = $.grep(iframe_content.styleSheets, function (el) {
                return el.title == 'gallery_preview_css_rules'
            });
            if (csssheet.length) {
                return csssheet[0];
            }


            var style = iframe_content.createElement('style');
            style.setAttribute('title', 'gallery_preview_css_rules');

            // WebKit hack :(
            style.appendChild(document.createTextNode(''));

            // Add the <style> element to the page
            iframe_content.head.appendChild(style);

            return style.sheet;
        },


        addCSSRule: function (gallery_id, first_image_file_id, index) {
            var sheet = this.getSheet();
            var rule = "background-image: url(" + fileUrl(first_image_file_id) + ")";
            var className = 'data-mce-image-gallery-placeholder-' + gallery_id;

            if ("insertRule" in sheet) {
                sheet.insertRule('.' + className + " {" + rule + "}", index ? index : 0);
            }

            else if ("addRule" in sheet) {
                sheet.addRule('.' + className, rule, index ? index : 0);
            }
            return className;
        },

        insertGallery: function (gallery_data) {
            editor.selection.collapse(true);
            editor.execCommand('mceInsertContent', false,
                '<img data-mce-placeholder ' +
                'width="' + gallery_data['width'] + '" height="' + gallery_data['height'] + '" ' +
                'src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///yH5BAEAAAAALAAAAAABAAEAAAIBRAA7" ' +
                'class="data-mce-image-gallery-placeholder ' +
                this.addCSSRule(gallery_data['id'], gallery_data['items'][0]['file_id']) +
                '" data-mce-image-gallery-placeholder>="' + gallery_data['id'] + '"');
        }
    };


    editor.addButton('gallery', {
        text: 'Gallery',
        icon: false,
        stateSelector: 'img[data-mce-gallery]',
        onclick: function () {
            var galleryElm = editor.selection.getNode();

            var defaultdata = {
                gallery_width: '200',
                gallery_height: '100'
            };
            var data = $.extend({}, defaultdata);
            if (galleryElm && galleryElm.nodeName == 'img' && galleryElm.getAttribute('data-mce-image-gallery-placeholder')) {

                if ($(galleryElm).attr('width')) {
                    data['gallery_width'] = $(galleryElm).attr('width');
                }

                if ($(galleryElm).attr('height')) {
                    data['gallery_height'] = $(galleryElm).attr('height');
                }

                if ($(galleryElm).attr('height')) {
                    data['gallery_height'] = $(galleryElm).attr('height');
                }
            } else {
                galleryElm = null;
            }

            var win = editor.windowManager.open({
                title: 'Article gallery',
                data: data,
                buttons: [
                    {
                        'text': "Save",
                        'classes': 'primary',
                        'onclick': function () {
                            var images = [];
                            $('li', '#' + win._id + ' .ul-sortable-images').each(function (index, $li) {
                                if (!$('input.pr-gallery-image-title', $li).is(':disabled')) {
                                    images.push({
                                        'id': $('.pr-gallery-image-id', $li).val(),
                                        'title': $('.pr-gallery-image-title', $li).val(),
                                        'copyright': $('.pr-gallery-image-copyright', $li).val(),
                                        'binary_data': $('img', $li).css('backgroundImage'),
                                    });
                                }
                            });
                            var data = win.toJSON();
                            editor.getParam('gallery_upload')({'parameters': data, 'images': images}).then(
                                function (gallery_data) {
                                    editor_controller.insertGallery(gallery_data);
                                    win.close()
                                }, function () {
                                    add_message('Error saving gallery')
                                }, function () {
                                    console.log(arguments)
                                });
                        }
                    }, {
                        'classes': 'image-gallery-upload',
                        'text': "Upload", onclick: function () {
                            $('.mce-sortable-images div input[type=file]').trigger('click');
                        }
                    }, {
                        'text': "Cancel",
                        'onclick': function () {
                            win.close();
                        }
                    }
                ],

                bodyType: 'form',
                body: [
                    {
                        type: 'container',
                        label: 'Dimensions',
                        layout: 'flex',
                        direction: 'row',
                        align: 'center',
                        spacing: 5,
                        items: [
                            {name: 'gallery_width', type: 'textbox', size: 3, ariaLabel: 'Width'},
                            {type: 'label', text: 'x'},
                            {name: 'gallery_height', type: 'textbox', size: 3, ariaLabel: 'Height'},
                        ]
                    }, {
                        type: 'container',
                        minHeight: 350,
                        minWidth: 500,
                        classes: 'sortable-images'
                    },
                ],
            });


            dialog_controller.init(win._id);
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