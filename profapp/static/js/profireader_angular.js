// /**
//  * Function calculates difference between two objects/arrays
//  * return array or object depending on type of second argument
//  * @param {type} a
//  * @param {type} b
//  * @param {type} notstrict - compare by == if true (if false/ommted by ===)
//  * @returns {Array/Object} with elements different in a and b. also if index is present only in one object (a or b)
//  * if returened element is array same object are reffered by 'undefined'
//  */
// function getObjectsDifference(a, b, setval, notstrict) {
//
//     'use strict';
//
//     if ((typeof a !== 'object') || (typeof b !== 'object')) {
//         console.log('getObjectsDifference expects both arguments to be array or object');
//         return null;
//     }
//
//     var ret = $.isArray(b) ? [] : {};
//
//     $.each(a, function (ind, aobj) {
//         if ((typeof aobj === 'object') && (typeof b[ind] === 'object')) {
//             if ((aobj === null) && (b[ind] === null)) {
//                 return;
//             }
//             var nl = getObjectsDifference(aobj, b[ind], setval, notstrict);
//             if (!$.isEmptyObject(nl)) {
//                 ret[ind] = nl;
//             }
//         }
//         else {
//             if ((notstrict && (a[ind] == b[ind])) || (!notstrict && (a[ind] === b[ind]))) {
//                 return;
//             }
//             ret[ind] = (setval === undefined) ? aobj : setval;
//         }
//     });
//     $.each(b, function (ind, bobj) {
//         if ((typeof bobj === 'object') && (typeof a[ind] === 'object')) {
//
//         }
//         else {
//             if ((notstrict && (a[ind] == b[ind])) || (!notstrict && (a[ind] === b[ind]))) {
//                 return;
//             }
//             ret[ind] = (setval === undefined) ? bobj : setval;
//         }
//     });
//     return ret;
// }

function quoteattr(s, preserveCR) {
    preserveCR = preserveCR ? '&#13;' : '\n';
    return ('' + s)/* Forces the conversion to string. */
        .replace(/&/g, '&amp;')/* This MUST be the 1st replacement. */
        .replace(/'/g, '&apos;')/* The 4 other predefined entities, required. */
        .replace(/"/g, '&quot;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        /*
         You may add other replacements here for HTML only
         (but it's not necessary).
         Or for XML, only if the named entities are defined in its DTD.
         */
        .replace(/\r\n/g, preserveCR)/* Must be before the next replacement. */
        .replace(/[\r\n]/g, preserveCR);
}


function resolveDictForAngularController(dict) {
    return _.object(_.map(dict, function (val, key) {
        return [key, function () {
            return val
        }]
    }))
}

var prDatePicker_and_DateTimePicker = function (name, $timeout) {
    return {
        require: 'ngModel',
        restrict: 'A',
        scope: {
            ngModel: '=',
            ngChange: '&'
        },
        link: function (scope, element, attrs, ngModelController) {

            var defformat = (name === 'prDatePicker') ? 'dddd, LL' : 'dddd, LL (HH:mm)';

            var format = (attrs[name] ? attrs[name] : defformat);
            element.addClass((name === 'prDatePicker') ? "pr-datepicker" : "pr-datetimepicker");

            ngModelController.$formatters = [function (d) {
                var m = moment(d);
                return m.isValid() ? m.format(format) : "";
            }];

            scope.$watch('ngModel', function (newdate, olddate) {

                var setdate = null;
                if (newdate) {
                    setdate = moment(newdate);
                    if (setdate.isValid() && (!olddate) && name === 'prDateTimePicker') {
                        var now = moment();
                        setdate.minutes(now.minutes());
                        setdate.hour(now.hour());
                    }
                }
                element.data("DateTimePicker").date(setdate);
                if (scope['ngChange'] && newdate !== olddate) {
                    $timeout(function () {
                        scope['ngChange']();
                    }, 0);
                }
            });

            var opt = {
                locale: window._LANG,
                keepInvalid: true,
                useCurrent: false,
                widgetPositioning: {
                    horizontal: 'left',
                    vertical: 'bottom'
                },
                format: format
            };
            if (name === 'prDateTimePicker') {
                opt['sideBySide'] = true;
            }
            element.datetimepicker(opt).on("dp.change", function (e) {
                $timeout(function () {
                    scope['ngModel'] = e.date ?
                        ((name === 'prDatePicker') ? moment(e.date).format('YYYY-MM-DD') : e.date.toISOString()) :
                        null;
                }, 0)

            })

        }

    }
}

angular.module('profireaderdirectives', ['ui.bootstrap', 'ui.bootstrap.tooltip', 'ui.select'])
    .factory('$membership_tags', ['$http', '$uibModal', function ($http, $uibModal) {
        return function (dict) {
            return modalInstance = $uibModal.open({
                templateUrl: 'membership_tags.html',
                controller: 'membership_tags',
                backdrop: 'static',
                keyboard: false,
                resolve: resolveDictForAngularController(dict)
            });
        }
    }])
    .controller('confirm_dialog_controller', function ($scope, $uibModalInstance, title, question, buttons) {

        $scope.buttons = buttons;
        $scope.title = title;
        $scope.question = question;
        $scope.ans = function (resp) {
            if (resp) {
                $uibModalInstance.close(resp)
            }
            else {
                $uibModalInstance.dismiss(resp)
            }
        }

    })
    .factory('$confirm', ['$uibModal', function ($uibModal) {
        return function (title, question, yes_text, no_text) {
            var modalInstance = $uibModal.open({
                templateUrl: 'confirm_dialog.html',
                controller: 'confirm_dialog_controller',
                resolve: {
                    'buttons': function () {
                        return [{'answer': true, 'text': yes_text ? yes_text : 'Ok', 'class_name': 'btn-success'},
                            {'answer': false, 'text': no_text ? no_text : 'Cancel', 'class_name': 'btn-danger'}];
                    },
                    'title': function () {
                        return title;
                    },
                    'question': function () {
                        return question;
                    }
                }
            });
            return modalInstance.result;
        }

    }])
    .controller('select_status_dialog_controller', function ($scope, $uibModalInstance, title,
                                                             old_status, status_changes, question, $timeout) {

        $scope.title = title;
        $scope.question = question;
        $scope.status_changes = status_changes;
        $scope.old_status = old_status;
        $scope.new_status = old_status;

        $scope.ok = function () {
            $uibModalInstance.close($scope.new_status)
        };
        $scope.cancel = $uibModalInstance.dismiss;
    })
    .factory('$selectStatus', ['$uibModal', function ($uibModal) {
        return function (dict, scope) {
            var modalInstance = $uibModal.open({
                templateUrl: 'select_status_dialog.html',
                controller: 'select_status_dialog_controller',
                scope: scope,
                resolve: resolveDictForAngularController(dict),
            });
            return modalInstance.result;
        }

    }])
    .factory('$ok', ['$http', '$q', function ($http, $q) {
        return function (url, data, ifok, iferror, translate) {
            //console.log($scope);
            function error(result, error_code, message) {
                if (iferror) {
                    iferror(result, error_code, message)
                }
                else {
                    add_message(result ? result : 'wrong answer from server', 'danger');
                }
                return $q.reject();
            }

            return $http.post(url, $.extend({}, data, translate ? {__translate: translate} : {})).then(
                function (response) {
                    if (!response || !response['data'] || typeof response['data'] !== 'object' || response === null) {
                        return error(null, -1, 'wrong response');
                    }

                    var resp = response['data'];

                    if (!resp['ok']) {
                        return error(resp['data'], resp['error_code'], resp['message']);
                    }

                    if (ifok) {
                        return ifok(resp['data']);
                    }
                    else {
                        return resp['data'];
                    }
                },
                function () {
                    return error(null, -1, 'wrong response');
                }
            );
        }
    }])
    .directive('prHelpTooltip', ['$compile', '$templateCache', '$controller', function ($compile, $templateCache, $controller) {
        return {
            restrict: 'E',
            link: function (scope, element, attrs) {
                element.html('<span uib-popover-html="\'' + quoteattr(scope.__('help tooltip ' + element.html())) + '\'" ' +
                    'popover-placement="' + (attrs['placement'] ? attrs['placement'] : 'bottom') + '" ' +
                    'popover-trigger="' + (attrs['trigger'] ? attrs['trigger'] : 'mouseenter') + '" ' +
                    'class="' + (attrs['classes'] ? attrs['classes'] : 'glyphicon glyphicon-question-sign') + '"></span>');
                $compile(element.contents())(scope);
            }
        }
    }])


    .directive('dateTimestampFormat', function () {
        return {
            require: 'ngModel',
            link: function (scope, element, attr, ngModelCtrl) {
                ngModelCtrl.$formatters.unshift(function (timestamp) {
                    if (timestamp) {
                        var date = new Date(timestamp * 1000);
                        return date;
                    } else
                        return "";
                });
                ngModelCtrl.$parsers.push(function (date) {
                    if (date instanceof Date) {
                        var timestamp = Math.floor(date.getTime() / 1000)
                        return timestamp;
                    } else
                        return "";
                });
            }
        };
    })
    .directive('prDateTimePicker', function ($timeout) {
        return prDatePicker_and_DateTimePicker('prDateTimePicker', $timeout);
    }).directive('prDatePicker', function ($timeout) {
    return prDatePicker_and_DateTimePicker('prDatePicker', $timeout);
})
    .directive('prDatepicker', function () {
        return {
            replace: false,
            require: 'ngModel',
            restrict: 'A',
            scope: {
                ngModel: '='
            },
            link: function (scope, element, attrs, model) {
                scope.$watch('ngModel', function (nv, ov) {
                    scope.setdate = scope['ngModel'];
                });
                scope.$watch('setdate', function (nv, ov) {
                    if (nv && nv.setHours) nv.setHours(12);
                    scope['ngModel'] = nv;
                });
            },
            template: function (ele, attrs) {
// TODO: MY BY OZ: please uncoment time (comented by ng-if=0 now), move date and time to one line
                return '<span><input style="width: 15em; display: inline" type="date" class="form-control" uib-datepicker-popup\
               ng-model="setdate" ng-required="true"\
               datepicker-options="dateOptions" close-text="Close"/><span class="input-group-btn"></span>\
               </span>';
            }
        }
    })
    .directive('highlighter', ['$timeout', function ($timeout) {
        return {
            restrict: 'A',
            link: function (scope, element, attrs) {
                scope.$watch(attrs.highlighter, function (nv, ov) {
                    if (nv !== ov) {
                        highlight($(element));
                    }
                });
            }
        };
    }])
    .directive('prImage', [function () {
        return {
            restrict: 'A',
            scope: {
                prImage: '=',
                prNoImage: '@',

            },
            link: function (scope, element, attrs) {
                var image_reference = attrs['prImage'].split('.').pop();
                var no_image = attrs['prNoImage'] ? attrs['prNoImage'] : false;

                if (!no_image) {
                    no_image = noImageForImageName(image_reference);
                }

                scope.$watch('prImage', function (newval, oldval) {
                    element.css({
                        backgroundImage: "url('" + fileUrl(newval, false, no_image) + "')"
                        // backgroundImage: "url('" + newval + "')"
                    });
                });
                element.attr('src', static_address('images/0.gif'));
                element.addClass('bg-contain');
            }
        };
    }]).directive('prImageWatch', [function () {
    return {
        restrict: 'A',
        scope: {
            prImageWatch: '=',
            prNoImage: '@',

        },
        link: function (scope, element, attrs) {
            var image_reference = attrs['prImageWatch'].split('.').pop();
            var no_image = attrs['prNoImage'] ? attrs['prNoImage'] : false;

            if (!no_image) {
                no_image = noImageForImageName(image_reference);
            }

            scope.$watch('prImageWatch', function (newval, oldval) {
                element.css({
                    backgroundImage: "url('" + fileUrl(newval, false, no_image) + "')"
                });
            });
            element.attr('src', static_address('images/0.gif'));
            element.addClass('bg-contain');
        }
    };
}])
    .directive('prImageUrl', [function () {
        return {
            restrict: 'A',
            scope: false,
            link: function (scope, element, attrs) {
                element.attr('src', static_address('images/0.gif'));
                element.css({
                    backgroundPosition: attrs['prImagePosition'] ? attrs['prImagePosition'] : 'center',
                    backgroundImage: 'url(' + attrs['prImageUrl'] + ')'
                });
                element.addClass('bg-contain');
            }
        };
    }]).directive('prImageUrlWatch', [function () {
    return {
        restrict: 'A',
        scope: {
            prImageUrlWatch: '=',
        },
        link: function (scope, element, attrs) {
            element.attr('src', static_address('images/0.gif'));
            element.addClass('bg-contain');
            scope.$watch('prImageUrlWatch', function (newval, oldval) {
                if (newval)
                    element.css({
                        backgroundPosition: attrs['prImagePosition'] ? attrs['prImagePosition'] : 'center',
                        backgroundImage: "url('" + newval + "')"
                    });
            });
        }
    };
}])
//TODO: SS by OZ: better use actions (prUserCan) not rights. action can depend on many rights
    .directive('prUserRights', function ($timeout) {
        return {
            restrict: 'AE',
            link: function (scope, element, attrs) {
                var elementType = element.prop('nodeName');
                scope.$watch(attrs['prUserRights'], function (val) {
                    disable(val)
                })

                var disable = function (allow) {
                    if (allow === false) {
                        if (elementType === 'BUTTON' || elementType === 'INPUT') {
                            element.prop('disabled', true)
                        } else if (elementType === 'A') {
                            element.css({'pointer-events': 'none', 'cursor': 'default'})
                        } else {
                            element.hide()
                        }
                    }
                }
            }
        };
    })
    .directive('prUserCan', function ($timeout) {
        return {
            restrict: 'AE',
            link: function (scope, element, attrs) {
                var elementType = element.prop('nodeName');
                var enable = function (allow) {
                    if (allow === true) {
                        element.prop('disabled', false);
                        element.removeClass('disabled');
                        element.prop('title', '');
                    } else {
                        if (elementType === 'BUTTON' || elementType === 'INPUT') {
                            element.prop('disabled', true);
                            element.prop('title', allow === false ? '' : allow);
                        } else if (elementType === 'A') {
                            element.addClass('disabled');
                            element.prop('title', allow === false ? '' : allow);
                        } else {
                            element.hide()
                        }

                    }
                }

                scope.$watch(attrs['prUserCan'], function (val) {
                    enable(val)
                })


            }
        };
    })
    .filter('html', ['$sce', function ($sce) {
        return function (text) {
            return $sce.trustAsHtml(text);
        };
    }]).filter('strip_html', function () {
    return function (text) {
        return $("<div>" + text + "</div>").text();
    };
});


areAllEmpty = function () {
    var are = true;

    $.each(arguments, function (ind, object) {
        if (are) {
            var ret = true;
            if ($.isArray(object)) {
                ret = object.length ? false : true;
            }
            else if ($.isPlainObject(object) && $.isEmptyObject(object)) {
                ret = true;
            }
            else {
                ret = ((object === undefined || object === false || object === null || object === 0) ? true : false);
            }
            are = ret;
        }
    });
    return are;
};


function file_choose(selectedfile) {
    console.log(selectedfile)
    var args = top.tinymce.activeEditor.windowManager.getParams();
    var win = (args.window);
    var input = (args.input);
    if (selectedfile['type'] === 'file_video') {
        win.document.getElementById(input).value = "https://youtu.be/" + selectedfile['youtube_data']['id'] + "?list=" + selectedfile['youtube_data']['playlist_id'];
    } else {
        win.document.getElementById(input).value = selectedfile['file_url'];
    }
    top.tinymce.activeEditor.windowManager.close();
}

// 'ui.select' uses static_address('js/select.js') included in _index_layout.html
//module = angular.module('Profireader', ['ui.bootstrap', 'profireaderdirectives', 'ui.tinymce', 'ngSanitize', 'ui.select']);

module = angular.module('Profireader', pr_angular_modules);

module.config(['$routeProvider', '$sceDelegateProvider',
    function ($routeProvider, $sceDelegateProvider) {
        $sceDelegateProvider.resourceUrlWhitelist(['self', new RegExp('^.*$')]);
    }]);

module.config(function ($provide) {
    $provide.decorator('$controller', function ($delegate) {
        return function (constructor, locals, later, indent) {
            if (typeof constructor === 'string' && !locals.$scope.controllerName) {
                locals.$scope.controllerName = constructor;
            }
            return $delegate(constructor, locals, later, indent);
        };
    });
})

Date.prototype.toISOString = function () {
    //console.log('Tue, 26 Jan 2016 13:59:14 GMT', this.toUTCString());
    return this.toUTCString();
    //dateFormat(this, "dddd, mmmm dS, yyyy, h:MM:ss TT");
    //  return 'here goes my awesome formatting of Date Objects '+ this;
};


module.controller('filemanagerCtrl', ['$scope', '$uibModalInstance', 'file_manager_called_for', 'file_manager_on_action',
    'file_manager_default_action', 'get_root',
    function ($scope, $uibModalInstance, file_manager_called_for, file_manager_on_action, file_manager_default_action, get_root) {

//TODO: SW fix this pls

        closeFileManager = function () {
            $scope.$apply(function () {
                $uibModalInstance.dismiss('cancel')
            });
        };

        $scope.close = function () {
            $uibModalInstance.dismiss('cancel');
        };
        $scope.src = '/filemanager/';
        var params = {};
        if (file_manager_called_for) {
            params['file_manager_called_for'] = file_manager_called_for;
        }
        if (file_manager_on_action) {
            params['file_manager_on_action'] = angular.toJson(file_manager_on_action);
        }

        if (file_manager_default_action) {
            params['file_manager_default_action'] = file_manager_default_action;
        }
        if (get_root) {
            params['get_root'] = get_root;
        }
        $scope.src = $scope.src + '?' + $.param(params);
    }]);

module.directive('ngEnter', function () {
    return function (scope, element, attrs) {
        element.bind("keydown keypress", function (event) {
            if (event.which === 13) {
                scope.$apply(function () {
                    scope.$eval(attrs.ngEnter, {'event': event});
                });

                event.preventDefault();
            }
        });
    };
});

function now() {
    return Date.now() / 1000;
}

var update_last_acessed_phrases = [];
var update_last_acessed_phrases_timer = null;

function pr_dictionary(phrase, dictionary, allow_html, scope, $ok, phrase_default, phrase_comment) {
    allow_html = allow_html ? allow_html : '';
    if (typeof phrase !== 'string') {
        return '';
    }
    // if (!scope.$$translate) {
    //     scope.$$translate = {};
    // }
    phrase = phrase.replace(/^(.*)\/\//g, '$1');
    phrase_comment = phrase_comment ? phrase_comment : null;
    phrase_default = phrase_default ? phrase_default : null;

    var t = now();
    //TODO OZ by OZ hasOwnProperty
    phrase = phrase.replace('\n', ' ').replace(/[\s]+/gi, ' ').trim();

    var CtrlName = scope.controllerName ? scope.controllerName : '';
    var phrase_dict;

    if (!scope.$$translate || !scope.$$translate[phrase]) {
        phrase_dict = {'lang': phrase_default ? phrase_default : phrase, 'time': t, allow_html: allow_html}
    }

    if (scope.$$translate) {
        if (!scope.$$translate[phrase]) {
            scope.$$translate[phrase] = phrase_dict;
            $ok('/tools/save_translate/', {
                template: CtrlName,
                phrase: phrase,
                phrase_comment: phrase_comment,
                phrase_default: phrase_default,
                allow_html: allow_html,
                url: window.location.href
            }, function (resp) {

            });
        }
        else {
            phrase_dict = scope.$$translate[phrase];
        }
    }


    if ((t - phrase_dict['time']) > 86400) {
        phrase_dict['time'] = t;
        update_last_acessed_phrases.push({
            template: CtrlName,
            phrase: phrase,
            phrase_comment: phrase_comment,
            phrase_default: phrase_default
        });
        if (window.update_last_acessed_phrases_timer) {
            clearTimeout(window.update_last_acessed_phrases_timer);
            window.update_last_acessed_phrases_timer = null;
        }
        window.update_last_acessed_phrases_timer = setTimeout(function () {
            $ok('/tools/update_translation_usage/', {'to_update': update_last_acessed_phrases}, function (resp) {
            });
            update_last_acessed_phrases = [];
        }, 3000);

    }

    // if (phrase_dict['allow_html'] !== allow_html  ) {
    //     phrase_dict['allow_html'] = allow_html;
    //     $ok('/tools/change_allowed_html/', {
    //         template: CtrlName,
    //         phrase: phrase,
    //         phrase_comment: phrase_comment,
    //         phrase_default: phrase_default,
    //         allow_html: allow_html
    //     }, function (resp) {
    //     });
    // }


    var ret = phrase_dict['lang'];
    ret = ret.replace(/%\(([^)]*)\)(s|d|f|m|i)/g, function (g0, g1) {
        var indexes = g1.split('.');
        var d = dictionary ? dictionary : scope;
        if (!d) {
            console.warn('passed object is False', d);
            return g1;
        }
        // try {
        for (var i in indexes) {
            if (typeof d === 'object' && d !== null && indexes[i] in d) {
                d = d[indexes[i]];
            }
            else {
                console.warn('can`t find ' + g1 + ' in passed dict', dictionary ? dictionary : scope);
                return g1;
            }
        }
        return d;
        // }
        // catch (a) {
        //     console.log(g0, g1);
        //     return g1
        // }
    });
    return ret;
}

module.run(function ($rootScope, $ok, $sce, $uibModal, $sanitize, $timeout, $templateCache) {
    //$rootScope.theme = 'bs3'; // bootstrap3 theme. Can be also 'bs2', 'default'
    angular.extend($rootScope, {
        fileUrl: function (file_id, down, if_no_file) {
            return fileUrl(file_id, down, if_no_file);
        },
        highlightSearchResults: function (full_text, search_text) {
            if (search_text !== '' && search_text !== undefined) {
                var re = new RegExp(search_text, "g");
                return $sce.trustAsHtml(full_text.replace(re, '<span style="color:blue">' + search_text + '</span>'));
            }
            return $sce.trustAsHtml(full_text);
        },
        strip_html: function () {

        },
        __: function (phrase, dictionary, phrase_default, phrase_comment) {
            return $sce.trustAsHtml(pr_dictionary(phrase, dictionary, '*', this, $ok, phrase_default, phrase_comment));
        },
        _: function (phrase, dictionary, phrase_default, phrase_comment) {
            return pr_dictionary(phrase, dictionary, '', this, $ok, phrase_default, phrase_comment);
        },

        publication_count_for_plan: function (plan, pub_type, already_published_counts, show_planed_counts) {
            var pub_type_upper = pub_type.toUpperCase();
            var pub_type_lower = pub_type.toLowerCase();

            function get_count(planed_count) {
                var holded = already_published_counts['by_status_visibility']['HOLDED'][pub_type_upper];
                var published = already_published_counts['by_status_visibility']['PUBLISHED'][pub_type_upper];
                if (planed_count !== false) {
                    if (planed_count < 0) {
                        published = published + holded;
                        holded = 0;
                    }
                    else if (planed_count == 0) {
                        holded = published + holded;
                        published = 0;
                    }
                    else {
                        var total = published + holded;
                        holded = total - planed_count;
                        holded = holded < 0 ? 0 : holded;
                        published = total - holded;
                    }
                }
                return '&nbsp;(<nothing class="publication-fg-STATUS-PUBLISHED">' + published + ',</nothing><nothing class="publication-fg-STATUS-HOLDED">' + holded + '</nothing>)';
            }

            if (!plan || !already_published_counts) {
                return '';
            }

            var ret = plan['publication_count_' + pub_type_lower];

            return (ret < 0 ? '&infin;' : (ret ? ret : '0')) + get_count(show_planed_counts ? ret : false);

        },

        moment: function (value, out_format) {
            return value ? moment.utc(value).local().format(out_format ? out_format : 'dddd, LL (HH:mm)', value) : ''
        },
        MAIN_DOMAIN: MAIN_DOMAIN,
        static_address: function (relative_file_name) {
            return static_address(relative_file_name);
        },
        highlight: function (text, search) {
            if (!search) {
                return $sce.trustAsHtml(text);
            }
            return $sce.trustAsHtml(text.replace(new RegExp(search, 'gi'), '<span class="ui-select-highlight">$&</span>'));
        },

        loadData: function (url, senddata, beforeload, afterload) {
            var scope = this;
            scope.loading = true;
            $ok(url ? url : '', senddata ? senddata : {}, function (data) {
                if (!beforeload) beforeload = function (d) {
                    return d;
                };
                scope.data = beforeload(data);
                scope.original_data = $.extend(true, {}, scope.data);
                if (afterload) afterload();

            }).finally(function () {
                scope.loading = false;
            });
        },
        areAllEmpty: areAllEmpty,
        chooseImageinFileManager: function (do_on_action, default_action, callfor, id) {
            var scope = this;
            var callfor_ = callfor ? callfor : 'file_browse_image';
            var default_action_ = default_action ? default_action : 'file_browse_image';
            var root_id = id ? id : '';
            scope.filemanagerModal = $uibModal.open({
                templateUrl: 'filemanager.html',
                controller: 'filemanagerCtrl',
                size: 'filemanager-halfscreen',
                resolve: {
                    file_manager_called_for: function () {
                        return callfor_
                    },
                    file_manager_on_action: function () {
                        return {
                            choose: do_on_action
                        }
                    },
                    file_manager_default_action: function () {
                        return default_action_
                    },
                    get_root: function () {
                        return root_id
                    }
                }
            });
        },
        loadNextPage: function (url, after_load) {
            var lnpf = function (onscroll) {
                var atend = onscroll ?
                    ($(window).scrollTop() >= $(document).height() - $(window).height() - 10) :
                    (($(document).height() - $(window).height() === 0));
                if (atend && !scope.loading && !scope.data.end) {
                    scope.next_page += 1;
                    scope.loading = true;
                    load();
                }
            }
            var scope = this;
            scope.next_page = 1;
            $(window).scroll(function () {
                if (scope.scroll_data) {
                    scope.scroll_data.next_page = scope.next_page
                }
                lnpf(true);
            });

            $timeout(lnpf, 500);
            var load = function () {
                $ok(url, scope.scroll_data ? scope.scroll_data : {next_page: scope.next_page}, function (resp) {
                    scope.data.end = resp.end;
                    after_load(resp);
                    scope.loading = false;
                }).finally(function () {
                    $timeout(function () {
                        lnpf();
                    }, 1000)
                });
            }
        },
        dateOptions: {
            formatYear: 'yy',
            startingDay: 1
        },
        tinymceDefaultOptions: {
            inline: false,
            menu: [],
            width: 750,
            plugins: 'advlist autolink link image charmap print paste table media',
            skin: 'lightgray',
            theme: 'modern',
            'toolbar1': "undo redo | bold italic | alignleft aligncenter alignright alignjustify | styleselect | bullist numlist outdent indent | media link image table",
            //'toolbar1': "undo redo | bold italic | alignleft aligncenter alignright alignjustify | styleselect | bullist numlist outdent indent | link image table"[*],
            'valid_elements': "iframe[*],img[*],table[*],tbody[*],td[*],th[*],tr[*],p[*],h1[*],h2[*],h3[*],h4[*],h5[*],h6[*],div[*],ul[*],ol[*],li[*],strong/b[*],em/i[*],span[*],blockquote[*],sup[*],sub[*],code[*],pre[*],a[*],object[*]",
            //init_instance_callback1: function () {
            //    console.log('init_instance_callback', arguments);
            //},
            file_browser_callback: function (field_name, url, type, win) {
                var cmsURL = '/filemanager/?file_manager_called_for=file_browse_' + type +
                    '&file_manager_default_action=choose&file_manager_on_action=' + encodeURIComponent(angular.toJson({choose: 'parent.file_choose'}));
                tinymce.activeEditor.windowManager.open({
                        file: cmsURL,
                        width: 950,  // Your dimensions may differ - toy around with them!
                        height: 700,
                        resizable: "yes",
                        //inline: "yes",  // This parameter only has an effect if you use the inlinepopups plugin!
                        close_previous: "yes"
                    }
                    ,
                    {
                        window: win,
                        input: field_name
                    }
                )
                ;

            },
            //valid_elements: Config['article_html_valid_elements'],
            //valid_elements: 'a[class],img[class|width|height],p[class],table[class|width|height],th[class|width|height],tr[class],td[class|width|height],span[class],div[class],ul[class],ol[class],li[class]',
            //TODO: OZ by OZ: select css for current theme. also look for another place with same todo
            content_css: [static_address('front/css/bootstrap.css'), static_address('css/article.css')],

            //paste_auto_cleanup_on_paste : true,
            //paste_remove_styles: true,
            //paste_remove_styles_if_webkit: true,
            //paste_strip_class_attributes: "all'),

            //style_formats: [
            //    {title: 'Bold text', inline: 'b'},
            //    {title: 'Red text', inline: 'span', styles: {color: '#ff0000'}},
            //    {title: 'Red header', block: 'h1', styles: {color: '#ff0000'}},
            //
            //    {
            //        title: 'Image Left',
            //        selector: 'img',
            //        styles: {
            //            'float': 'left',
            //            'margin': '0 10px 0 10px'
            //        }
            //    },
            //    {
            //        title: 'Image Right',
            //        selector: 'img',
            //        styles: {
            //            'float': 'right',
            //            'margin': '0 0 10px 10px'
            //        }
            //    }
            //]

        }
    })
});


// function cleanup_html(html) {
//     normaltags = '^(span|a|br|div|table)$';
//     common_attributes = {
//         whattr: {'^(width|height)$': '^([\d]+(.[\d]*)?)(em|px|%)$'}
//     };
//
//     allowed_tags = {
//         '^table$': {allow: '^(tr)$', attributes: {whattr: true}},
//         '^tr$': {allow: '^(td|th)$', attributes: {}},
//         '^td$': {allow: normaltags, attributes: {whattr: true}},
//         '^a$': {allow: '^(span)$', attrсibutes: {'^href$': '.*'}},
//         '^img$': {allow: false, attributes: {'^src$': '.*'}},
//         '^br$': {allow: false, attributes: {}},
//         '^div$': {allow: normaltags, attributes: {}}
//     };
//
//     $.each(allowed_tags, function (tag, properties) {
//         var attributes = properties.attributes ? properties.attributes : {}
//         $.each(attributes, function (attrname, allowedvalus) {
//             if (allowedvalus === true) {
//                 allowed_tags[tag].attributes[attrname] = common_attributes[attrname] ? common_attributes[attrname] : '.*';
//             }
//         });
//     });
//
//     var tags = html.split(/<[^>]*>/);
//
//     $.each(tags, function (tagindex, tag) {
//         console.log(tagindex, tag);
//     });
//
//     return html;
// }


None = null;
False = false;
True = true;

$.fn.scrollTo = function () {
    return this.each(function () {
        $('html, body').animate({
            scrollTop: $(this).offset().top
        }, 1000);
    });
};

function scrool($el) {
    $($el).scrollTo();
}

function highlight($el) {
    $($el).addClass('highlight');
    setTimeout(function () {
        $($el).removeClass('highlight');
    }, 35000);
};

function tinymceExtendSettings(toExtend, extendWith, key, extendSeparator) {
    if (!key) {
        $.extend(true, toExtend, extendWith);
        return toExtend;
    }

    if (key in toExtend) {
        if (typeof extendWith == 'string') {
            toExtend[key] += (extendSeparator + extendWith)
        }
        else if (Array.isArray(extendWith)) {
            toExtend[key] = toExtend[key].concat(extendWith);
        }
        else {
            $.extend(true, toExtend, {key: extendWith});
        }
    }
    else {
        toExtend[key] = extendWith;
    }
    return toExtend;
};

function angularControllerFunction(controller_attr, function_name) {
    var nothing = function () {
    };
    var el = $('[ng-controller=' + controller_attr + ']');
    if (!el && !el.length) return nothing;
    if (!angular.element(el[0])) return nothing;
    if (!angular.element(el[0]).scope()) return nothing;
    if (!angular.element(el[0]).scope()) return nothing;
    var func = angular.element(el[0]).scope()[function_name];
    var controller = angular.element(el[0]).controller();
    return (func && controller) ? func : nothing;
}

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

function cloneObject(o) {
    return (o === null || typeof o !== 'object') ? o : $.extend(true, {}, o);
}

function add_message(amessage, atype, atime, aunique_id) {
    return angularControllerFunction('message-controller', 'add_message')(amessage, atype, atime, aunique_id);
}


function getLengthOfAssociativeArray(array) {
    return Object.keys(array).length
}

function randomHash() {
    var text = "";
    var possible = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
    for (var i = 0; i < 32; i++)
        text += possible.charAt(Math.floor(Math.random() * possible.length));
    return text;
}

function buildAllowedTagsAndAttributes() {

    var class_prefix_general = 'pr_article_';
    var class_prefix_theme = 'pr_article_birdy';

    var general_classes = {
        'text_size': 'big,bigger,biggest,smallest,small,smaller,normal',
        'text_decoration': 'underline,normal',
        'text_style': 'b,i',
        'text_script': 'sup,sub',
        'float': 'left,right'
    };

    var theme_classes = {
        'text_color': 'red,gray,normal',
        'background_color': 'gray,normal'
    };

    var text_classes = ['text_size', 'text_decoration', 'text_style', 'text_script', 'text_color', 'background_color'];
    var layout_classes = ['float'];
    var wh_styles = {'width': '^[^d]*(px|em)$', 'height': '^[^d]*(px|em)$'};

    var allowed_tags_skeleton = [
        {
            tags: 'div,table,columns',
            classes: [].concat(text_classes, layout_classes)
        },
        {
            tags: 'div,table',
            styles: wh_styles
        },
        {
            tags: 'img',
            styles: wh_styles,
            classes: layout_classes
        },
        {
            tags: 'columns',
            attributes: {'number': '.*'}
        }
    ];

    var allowed_tags = {};
    $.each(allowed_tags_skeleton, function (del_ind, tags_and_properties) {

        var tags = tags_and_properties['tags'].split(',');

        var styles = tags_and_properties['styles'] ? tags_and_properties['styles'] : {};
        var attributes = tags_and_properties['attributes'] ? tags_and_properties['attributes'] : {};
        var classes = tags_and_properties['classes'] ? tags_and_properties['classes'] : {};


        $.each(tags, function (del_ind2, tag) {

            if (!allowed_tags[tag]) allowed_tags[tag] = {'classes': [], 'attributes': {}, 'styles': {}};

            $.each(styles, function (style_name, allowed_style_regexp) {
                if (allowed_tags[tag]['styles'][style_name]) {
                    console.error('error. regexp for style `' + style_name + '` for tag `' + tag + '` already defined as `' + allowed_tags[tag]['styles'][style_name] + '` ignored');
                }
                else {
                    allowed_tags[tag]['styles'][style_name] = allowed_style_regexp;
                }
            });

            $.each(attributes, function (attr_name, allowed_attr_regexp) {
                if (allowed_tags[tag]['attributes'][attr_name]) {
                    console.error('error. regexp for attribute `' + attr_name + '` for tag `' + tag + '` already defined as `' + allowed_tags[tag]['attributes'][attr_name] + '` ignored');
                }
                else {
                    allowed_tags[tag]['attributes'][attr_name] = allowed_attr_regexp;
                }
            });

            $.each(classes, function (del_ind3, classes_group_index) {
                if (theme_classes[classes_group_index]) {
                    class_sufixes = theme_classes[classes_group_index];
                }
                else if (general_classes[classes_group_index]) {
                    class_sufixes = general_classes[classes_group_index];
                }

                if (!class_sufixes) {
                    console.error('error. unknown class group index `' + classes_group_index + '` for tag `' + tag + '`. ignored');
                }
                else {
                    if (!allowed_tags[tag]['classes'][classes_group_index]) allowed_tags[tag]['classes'][classes_group_index] = [];
                    allowed_tags[tag]['classes'][classes_group_index] = [].concat(allowed_tags[tag]['classes'][classes_group_index],
                        _.map(class_sufixes.split(','), function (classsufix) {
                            return 'pr_article_' + classes_group_index + '_' + classsufix;
                        }));
                }
            });
        });
    });

    return allowed_tags;
}

function find_and_build_url_for_endpoint(dict, rules, host) {

    var found = false;
    var dict1 = {};

    // $.each(rules, function (ind, rule) {
    //     var ret = rule;
    //     var prop = null;
    //     var dict1 = $.extend({}, dict);
    //     for (prop in dict1) {
    //         ret = ret.replace('<' + prop + '>', dict[prop]);
    //         delete dict1[prop];
    //     }
    //     if (!ret.match('<[^<]*>')) {
    //         found = ret;
    //         return false;
    //     }
    // });


    $.each(rules, function (ind, rule) {
        var ret = '';
        var dict1 = $.extend({}, dict);
        $.each(rule, function (ind1, match) {
            if (typeof match == 'string') {
                ret = ret + match;
            }
            else {
                if (match['name'] in dict1) {
                    var r = dict1[match['name']];
                    if ('to_url_javascript' in match) {
                        r = eval('(' + match['to_url_javascript'] + ')("' + r + '")');
                    }
                    ret += r;
                    delete dict1[match['name']];
                }
                else {
                    ret = false;
                    return false;
                }
            }
        });

        if (ret !== false) {
            found = ret;
            return false;
        }
    });


    if (found === false) {
        console.error('Can`t found flask endpoint for passed dictionary', dict, rules);
        return '';
    }
    else {
        if (_.size(dict1) > 0) {
            console.warn("Too many parameters passed in dictionary for endpoint rule", dict, rules);
        }
        return (host ? ('//' + host) : '') + found;
    }
}

var compile_regexps = function (format_properties) {
    //var rem = format_properties['remove_classes_on_apply'] ?
    //    RegExp('^' + format_properties['remove_classes_on_apply'] + '$', "i") : false;
    //console.log(format_properties);

    var rem = false;
    if (format_properties['remove_classes_on_apply']) {
        rem = {};
        $.each(format_properties['remove_classes_on_apply'], function (del, class_to_rem) {
            rem[class_to_rem] = RegExp('^' + class_to_rem + '$', "i")
        });
    }

    var add = false;
    if (format_properties['add_classes_on_apply']) {
        add = {};
        $.each(format_properties['add_classes_on_apply'], function (class_to_add, check_if_not_exust) {
            add[class_to_add] = RegExp('^' + check_if_not_exust + '$', "i")
        });
    }
    delete format_properties['add_classes_on_apply'];
    delete format_properties['remove_classes_on_apply'];
    //console.log({remove: rem, add: add});
    return {remove: rem, add: add};
};

var add_or_remove_classes = function (element, classes, remove, add) {

    console.log(element, classes, remove, add);

    classes.map(function (class_name) {
        if (add) {
            $.each(add, function (add_if_not_exist, check_if_exist) {
                if (check_if_exist && class_name.match(check_if_exist)) {
                    delete add[add_if_not_exist];
                }
            });
        }
    });

    $.each(add, function (add_if_not_exist, check_if_exist) {
        $(element).addClass(add_if_not_exist);
    });

    $.each(remove, function (del, remove_regexp) {
        classes.map(function (class_name) {
            if (class_name.match(remove_regexp))
                $(element).removeClass(class_name);
        });

    });
};

var extract_formats_items_from_group = function (formats_in_group) {
    var ret = [];
    $.each(formats_in_group, function (format_name, format) {
        ret.push(
            {title: format_name.replace(/.*_(\w+)$/, '$1'), format: format_name});
    });
    return ret;
};


var get_complex_menu = function (formats, name, subformats) {
    var ret = [];
    $.each(subformats, function (del, group_label) {
        ret.push({
            'title': group_label,
            items: extract_formats_items_from_group(formats[name + '_' + group_label])
        });
    });
    return ret;
};

var get_array_for_menu_build = function (formats) {
    var menu = {};
    menu['foreground'] = [{items: extract_formats_items_from_group(formats['foreground_color'])}];
    menu['background'] = [{items: extract_formats_items_from_group(formats['background_color'])}];
    menu['font'] = [{items: extract_formats_items_from_group(formats['font_family'])}];
    menu['border'] = get_complex_menu(formats, 'border', ['placement', 'type', 'width', 'color']);
    menu['margin'] = get_complex_menu(formats, 'margin', ['placement', 'size']);
    menu['padding'] = get_complex_menu(formats, 'padding', ['placement', 'size']);


    //menu['background_color'] = {
    //    'title': 'background',
    //    'items': extract_formats_items_from_group(formats['background_color'])
    //};
    //menu['font_family'] = {'title': 'font', 'items': extract_formats_items_from_group(formats['font_family'])};
    //
    //$.each(formats, function (format_group_name, formats_in_group) {
    //    var ret1 = {'title': format_group_name, 'items': []};
    //    $.each(formats_in_group, function (format_name, format) {
    //        ret1['items'].push(
    //            {title: format_name.replace(/.*_(\w+)$/, '$1'), format: format_name});
    //    });
    //    ret.push(ret1);
    //});
    return menu;
};


var convert_python_format_to_tinymce_format = function (python_format) {

    if (python_format['remove_classes_on_apply'] || python_format['add_classes_on_apply']) {

        var rem_add = compile_regexps(python_format);

        python_format['onformat'] = function (DOMUtils, element) {
            var classes = $(element).attr('class');
            add_or_remove_classes(element, classes ? classes.split(/\s+/) : [], rem_add['remove'], rem_add['add']);
        }
    }
    return python_format;
};


// #TODO: OZ by OZ: remove this function. urls should be formed at ss
var noImageForImageName = function (image_name) {
    if (image_name === 'logo_file_id') {
        return static_address('images/company_no_logo.png');
    }
    else {
        return static_address('images/no_image.png');
    }
};

var dict_deep_get = function () {
    var args = Array.prototype.slice.call(arguments);
    var dict = args.shift();
    $.each(args, function (ind, k) {
        dict = dict[k];
    });
    return dict;
};


var find_index_by_keys = function () {
    var args = Array.prototype.slice.call(arguments);
    var list = args.shift();
    var val = args.shift();
    var ret = -1;
    $.each(list, function (ind, dict) {
        if (dict_deep_get.apply(this, [dict].concat(args)) == val) {
            ret = ind;
            return false;
        }
    });
    return ret;
};

var find_index_by_id = function (list, id) {
    return find_index_by_keys(list, id, 'id');
};

var find_by_keys = function () {
    var args = Array.prototype.slice.call(arguments);
    var list = args[0];
    var ind = find_index_by_keys.apply(this, args);
    return ind > -1 ? list[ind] : null;
};

var find_by_id = function (list, id) {
    var ind = find_index_by_keys(list, id, 'id');
    return ind > -1 ? list[ind] : null;
};


publication_counts_span = function (status, visibility, cnt, classes) {
    return '<span class="tar ' + (classes ? classes : '') + ' pr-grid-publications-vs publication-fg-STATUS-' + status + ' publication-bg-VISIBILITY-' + visibility + '">' + cnt + '</span>';
};

publications_counts_by_status_and_visibility_cell = function (value) {
    var all_statuses = ['PUBLISHED', 'HOLDED', 'SUBMITTED', 'UNPUBLISHED', 'DELETED'];
    var all_visibilities = ['OPEN', 'REGISTERED', 'PAYED'];
    var ret = [];
    $.each(all_visibilities,
        function (ind, visibility) {
            ret.push(publication_counts_span('PUBLISHED', visibility, value['by_status_visibility']['PUBLISHED'][visibility]));
        });
    return publication_counts_span('PUBLISHED', '', value['by_status']['PUBLISHED'], 'bold') + '</span> = ' + ret.join('+');
};

publications_counts_by_status_and_visibility_tooltip = function (value) {
    var ret = [];
    var all_statuses = ['PUBLISHED', 'HOLDED', 'SUBMITTED', 'UNPUBLISHED', 'DELETED'];
    var all_visibilities = ['OPEN', 'REGISTERED', 'PAYED'];

    $.each(all_statuses, function (ind, status) {
        var by_visibility = value['by_status_visibility'][status];
        var ret_v = [];
        $.each(all_visibilities, function (ind1, visibility) {
            ret_v.push(publication_counts_span(status, visibility, by_visibility[visibility]));
        });
        ret.push('<span class="publication-fg-STATUS-' + status + '">' + status + ': ' + publication_counts_span(status, '', value['by_status'][status], 'bold') + '</span> = ' + ret_v.join('+'));
    });
    var ret_v = [];

    $.each(all_visibilities, function (ind, visibility) {
        ret_v.push(publication_counts_span('', visibility, value['by_visibility'][visibility], 'italic black'));
    });

    ret.push('<span class="italic black">ALL: ' + publication_counts_span('', '', value['all'], 'bold') + '</span> = ' + ret_v.join('+'));
    return '<div class="tar nowrap">' + ret.join('</div><div class="tar nowrap">') + '</div>';
};

publication_column = function () {
    return {
        name: 'publications',
        width: '185',
        'uib-tooltip-html': function (row, value) {
            return publications_counts_by_status_and_visibility_tooltip(value);
        },
        render: function (row, value) {
            return publications_counts_by_status_and_visibility_cell(value);
        }
    };
};

window.lastUserActivity = now();
window.onUserActivity = {};
$('body').bind('mousedown keydown', function (event) {
    window.lastUserActivity = now();
    $.each(window.onUserActivity, function (ind, func) {
        func();
    })
});

