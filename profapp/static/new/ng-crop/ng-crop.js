/**
 * Created by oles on 07.04.16.
 */

(function (angular) {

    'use strict';
    if (!angular) {
        throw 'No angular found';
    }

    var r = function (f) {
        return Math.round(f * 1000) / 1000;
    }

    var px = function (n) {
        return ('' + n + 'px');
    }

    var inRange = function (v, min, max) {
        return Math.min(Math.max(min, v), max);
    };

    var createCompass = function (f) {
        return {w: f, e: f, s: f, n: f};
    };

    var compileTemplate = function ($scope, $compile, element) {
        element.html('<div class="ng-crop-container">' +
            '<div class="ng-crop-loading"></div>' +
            '<div class="ng-crop-canvas">' +
            '<img class="ng-crop-img"/>' +
            '<div ng-crop-action="set" class="ng-crop-set"></div>' +
            '<div ng-crop-action="move" class="ng-crop-move"></div>' +
            '<div ng-crop-action="nw" class="ng-crop-resize ng-crop-rect-n ng-crop-rect-w"></div>' +
            '<div ng-crop-action="n" class="ng-crop-resize ng-crop-rect-n"></div>' +
            '<div ng-crop-action="ne" class="ng-crop-resize ng-crop-rect-n ng-crop-rect-e"></div>' +
            '<div ng-crop-action="e" class="ng-crop-resize ng-crop-rect-e"></div>' +
            '<div ng-crop-action="se" class="ng-crop-resize ng-crop-rect-s ng-crop-rect-e"></div>' +
            '<div ng-crop-action="s" class="ng-crop-resize ng-crop-rect-s"></div>' +
            '<div ng-crop-action="sw" class="ng-crop-resize ng-crop-rect-s ng-crop-rect-w"></div>' +
            '<div ng-crop-action="w" class="ng-crop-resize ng-crop-rect-w"></div>' +
            '</div></div>');

        $compile(element.contents())($scope);
    }

    var collectElements = function ($scope, element) {

        $scope.$e = function (selector) {
            return $(selector, element);
        };

        $scope.$element_actions = $scope.$e('*[ng-crop-action]');

        $scope.$element_corners = $scope.$e('.ng-crop-resize');
        $scope.$element_corners_w = $scope.$e('.ng-crop-rect-w');
        $scope.$element_corners_e = $scope.$e('.ng-crop-rect-e');
        $scope.$element_corners_n = $scope.$e('.ng-crop-rect-n');
        $scope.$element_corners_s = $scope.$e('.ng-crop-rect-s');

        $scope.$element_action_move = $scope.$e('.ng-crop-move');
        $scope.$element_action_set = $scope.$e('.ng-crop-set');

        $scope.$img = $scope.$e('img');
        $scope.$canvas = $scope.$e('.ng-crop-canvas');
        $scope.$container = $scope.$e('.ng-crop-container');
        $scope.$loading = $scope.$e('.ng-crop-loading');
    }

    var Logic = function (img, opts, $container) {

        this.canvas2imgX = function (cx, state) {
            return r((cx + state.x) / state.zoom);
        };

        this.canvas2imgY = function (cy, state) {
            return r((cy + state.y) / state.zoom);
        };

        this.canvas2imgW = function (w, state) {
            return r(w / state.zoom);
        };

        this.canvas2imgH = function (h, state) {
            return r(h / state.zoom);
        };

        this.img2canvasX = function (ix, state) {
            return ix * state.zoom - state.x;
        };

        this.img2canvasW = function (w, state) {
            return w * state.zoom;
        };

        this.img2canvasH = function (h, state) {
            return h * state.zoom;
        };

        this.img2canvasY = function (iy, state) {
            return iy * state.zoom - state.y;
        };

        this.canvas2imgrect = function (canvasrect, state) {
            return canvasrect ? [
                this.canvas2imgX(canvasrect[0], state), this.canvas2imgY(canvasrect[1], state),
                this.canvas2imgX(canvasrect[2], state), this.canvas2imgY(canvasrect[3], state)] : null;
        };

        this.img2canvasRect = function (imgrect, state) {
            return imgrect ? [
                this.img2canvasX(imgrect[0], state), this.img2canvasY(imgrect[1], state),
                this.img2canvasX(imgrect[2], state), this.img2canvasY(imgrect[3], state)] : null;
        };

        this.relativeDeviation = function (v, in_respect_to) {
            return Math.abs(v - in_respect_to) / in_respect_to;
        };

        this.autoState = function () {
            return {zoom: this.ctr.min_zoom, x: 0, y: 0};
        }

        this.autoRect = function () {
            return [this.ctr.canvas[0] / 10., this.ctr.canvas[1] / 10., this.ctr.canvas[0] * 9 / 10., this.ctr.canvas[1] * 9 / 10.];
        }


        this.scale = function (canvasrect, state, compass) {
            // scale canvas rect by image constrains (min/max size, aspect) and canvas size
            var ret = [canvasrect[0], canvasrect[1], canvasrect[2], canvasrect[3]];
            var imgrect = this.canvas2imgrect(canvasrect, state);
            var max_w = this.ctr.max_width;
            var max_h = this.ctr.max_height;
            var min_w = this.ctr.min_width;
            var min_h = this.ctr.min_height;

            var asp = (imgrect[2] - imgrect[0]) / (imgrect[3] - imgrect[1]);

            if (asp > this.ctr.max_aspect) {
                // console.log('aspect >');

                max_w = (imgrect[3] - imgrect[1]) * this.ctr.max_aspect;
                if (max_w < this.ctr.min_width) {
                    max_w = this.ctr.min_width;
                }
                else if (max_w > this.ctr.max_width) {
                    throw new RangeError;
                }

            }
            else if (asp < this.ctr.min_aspect) {
                // console.log('aspect <');

                max_h = (imgrect[2] - imgrect[0]) / this.ctr.min_aspect;
                if (max_h < this.ctr.min_height) {
                    max_h = this.ctr.min_height;
                }
                else if (max_h > this.ctr.max_height) {
                    throw new RangeError;
                }
            }

            if (imgrect[2] - imgrect[0] > max_w) {
                // console.log('w >', imgrect[2] - imgrect[0], max_w);
                ret[0] = this.img2canvasX(imgrect[0] + compass.w * (imgrect[2] - imgrect[0] - max_w), state);
                ret[2] = this.img2canvasX(imgrect[2] + compass.e * (imgrect[0] - imgrect[2] + max_w), state);
            }
            else if (imgrect[2] - imgrect[0] < min_w) {
                // console.log('w <', imgrect[2] - imgrect[0], min_w);
                ret[0] = this.img2canvasX(imgrect[0] + compass.w * (imgrect[2] - imgrect[0] - min_w), state);
                ret[2] = this.img2canvasX(imgrect[2] + compass.e * (imgrect[0] - imgrect[2] + min_w), state);
            }

            if (imgrect[3] - imgrect[1] > max_h) {
                // console.log('h >', imgrect[3] - imgrect[1], max_h);
                ret[1] = this.img2canvasY(imgrect[1] + compass.n * (imgrect[3] - imgrect[1] - max_h), state);
                ret[3] = this.img2canvasY(imgrect[3] + compass.s * (imgrect[1] - imgrect[3] + max_h), state);
            }
            else if (imgrect[3] - imgrect[1] < min_h) {
                // console.log('h <', imgrect[3] - imgrect[1], min_h);
                ret[1] = this.img2canvasY(imgrect[1] + compass.n * (imgrect[3] - imgrect[1] - min_h), state);
                ret[3] = this.img2canvasY(imgrect[3] + compass.s * (imgrect[1] - imgrect[3] + min_h), state);
            }
            return ret;
        };

        this.fitByImageRect = function (canvasrect, state, compass) {

            var ret = this.scale(canvasrect, state, compass);
            // console.log('this.fitByImageRect',canvasrect, ret);

            // image scaled by max min size and aspect ratio go out of cancas
            // let' try move it
            var ret_copy = ret.slice();
            if (ret[0] < 0) {
                ret[2] = ret[2] - ret[0];
                ret[0] = 0;
            }
            if (ret[1] < 0) {
                ret[3] = ret[3] - ret[1];
                ret[1] = 0;
            }
            if (ret[3] > this.ctr.canvas[1]) {
                ret[1] = ret[1] - (ret[3] - this.ctr.canvas[1]);
                ret[3] = this.ctr.canvas[1];
            }
            if (ret[2] > this.ctr.canvas[0]) {
                ret[0] = ret[0] - (ret[2] - this.ctr.canvas[0]);
                ret[2] = this.ctr.canvas[0];
            }

            // ok, still out of canvas. let's try scale it
            if (ret[0] < 0 || ret[1] < 0) {
                if (ret[2] - ret[0] > this.ctr.canvas[0]) {
                    ret[0] = 0;
                    ret[2] = this.ctr.canvas[0];
                }
                if (ret[3] - ret[1] > this.ctr.canvas[1]) {
                    ret[1] = 0;
                    ret[3] = this.ctr.canvas[1];
                }
                ret = this.scale(ret, compass, true);
                if (ret[2] - ret[0] > this.ctr.canvas[0] || ret[3] - ret[1] > this.ctr.canvas[1]) {
                    return false;
                }
            }

            return ret;
        }


        this.addDXDY = function (canvasrect, mousedxdy) {

            var ret = [canvasrect[0], canvasrect[1], canvasrect[2], canvasrect[3]];
            mousedxdy = mousedxdy ? mousedxdy : [0, 0];

            if (mousedxdy.length === 2) mousedxdy.push(mousedxdy[0], mousedxdy[1]);

            for (var i = 0; i < 4; i++) ret[i] += mousedxdy[i];
            return ret;
        };

        this.normalizeState = function (newstate) {
            return {
                x: 0,
                y: 0,
                zoom: newstate['zoom'] ? newstate['zoom'] : this.ctr.min_zoom
            }
        }

        this.resizeRect = function (current_cr, state, compass) {

            try {
                compass = compass ? compass : createCompass(0.5);

                var cr = this.fitByImageRect(current_cr, state, compass);
                if (!cr) {
                    // cr = this.fitByImageRect(fitcr, compass, true);
                    // if (!cr) {
                    return false;
                    // }
                }

                return cr;
            }
            catch (e) {
                console.error(e);
                return false;
            }

        };

        this.calculateConstrains = function () {
            var o = opts;

            if (!img) {
                this.ctr = null;
                return false;
            }

            if (img.naturalWidth < o['min_width']) {
                throw new RangeError("Image to narrow for minimal width");
            }
            if (img.naturalHeight < o['min_height']) {
                throw new RangeError("Image to narrow for minimal height");
            }


            // TODO: check mage size and min/max can be meet
            // var aspect = img.naturalWidth / img.naturalHeight;
            // if (aspect)
            //
            //


            var ctr = {};
            ctr.image_size = [img.naturalWidth, img.naturalHeight];
            ctr.max_width = Math.min(ctr.image_size[0], o['max_width']);
            ctr.max_height = Math.min(ctr.image_size[1], o['max_height']);
            ctr.min_width = Math.max(1, o['min_width']);
            ctr.min_height = Math.max(1, o['min_height']);
            ctr.max_aspect = Math.min(Infinity, o['max_aspect']);
            ctr.min_aspect = Math.max(0, o['min_aspect']);
            ctr.max_zoom = o.max_zoom;


            var image_wider_than_container = ctr.image_size[0] * $container.height() / ctr.image_size[1] / $container.width();
            var img_based_min_zoom = 0;
            ctr.canvas = [0, 0];
            if (image_wider_than_container > 1) {
                img_based_min_zoom = $container.width() / ctr.image_size[0];
                ctr.canvas = [$container.width(), $container.height() / image_wider_than_container];
            }
            else {
                img_based_min_zoom = $container.height() / ctr.image_size[1];
                ctr.canvas = [$container.width() * image_wider_than_container, $container.height()];
            }

            // shrink canvas if min zoom overfit container
            if (img_based_min_zoom > ctr.max_zoom) {
                ctr.canvas = [ctr.canvas[0] / (img_based_min_zoom / ctr.max_zoom), ctr.canvas[1] / (img_based_min_zoom / ctr.max_zoom)];
                img_based_min_zoom = ctr.max_zoom;
            }

            ctr.min_zoom = Math.max(o.min_zoom, img_based_min_zoom);

            return ctr;

        };

        this.ctr = this.calculateConstrains();

    }

    var cropLinkFunc = function ($scope, $q, $timeout, element, attrs, model) {


        $scope.loading = true;
        $scope.img = null;
        $scope.url = null;
        $scope.logic = null;
        $scope.options = null;
        $scope.redraw_image = false;
        $scope.redraw_canvas = false;
        $scope.redraw_rect = false;

        $scope.$watch('ngCropOptions', function (newv, oldv) {

            // console.log(newv);

            var opts = {}

            var isnum = function (newval, key, already_assigned_opts) {
                return (typeof newval === 'number') ? true : (key + " should be number");
            };

            var isnumandgt1 = [1, isnum, function (newval, key, already_assigned_opts) {
                return (newval >= 1) ? true : (key + " should be > 1");
            }];
            var isnumandgt0 = [0, isnum, function (newval, key, already_assigned_opts) {
                return (newval >= 0) ? true : (key + " should be > 0");
            }];
            var isnumandi = [Infinity, isnum];


            angular.forEach({
                'min_zoom': isnumandgt0,
                'max_zoom': isnumandgt1.concat([function (newval, key, already_assigned_opts) {
                    return (newval >= already_assigned_opts['min_zoom']) ? true : " max_zoom is < min_zoom";
                }]),

                'min_width': isnumandgt1,
                'max_width': isnumandi.concat([function (newval, key, already_assigned_opts) {
                    return (newval >= already_assigned_opts['min_width']) ? true : " max_width is < min_width";
                }]),
                'min_height': isnumandgt1,
                'max_height': isnumandi.concat([function (newval, key, already_assigned_opts) {
                    return (newval >= already_assigned_opts['min_height']) ? true : " max_height is < min_height";
                }]),
                'min_aspect': isnumandgt0,
                'max_aspect': isnumandi.concat([function (newval, key, already_assigned_opts) {
                    return (newval >= already_assigned_opts['min_aspect']) ? true : " max_aspect is < min_aspect";
                }]),
            }, function (def_and_cond, key) {
                var default_value = def_and_cond[0];
                var some_condition_broken = !newv || !newv.hasOwnProperty || !newv.hasOwnProperty(key);
                if (!some_condition_broken) {
                    var newvalue = newv[key];
                    for (var i = 1; i < def_and_cond.length; i++) {
                        var check_condition = def_and_cond[i](newvalue, key, opts);
                        if (check_condition !== true) {
                            some_condition_broken = true;
                            console.error(check_condition);
                        }
                    }
                }
                opts[key] = some_condition_broken ? default_value : newvalue;
            });

            $scope.options = opts;

            $scope.setNewLogic(new Logic($scope.img, $scope.options, $scope.$container), true);

            $scope.redraw_canvas = true;

            $timeout($scope.draw);

        });


        // 'ngCropDisabled',
        $scope.$watchGroup(['ngCrop', 'ngCropCoordinates', 'ngCropState', 'ngCropDisabled'], function (newv, oldv) {
            // console.log(newv[0]);
            var ff = function (i, n, o) {
                if (n !== o) {
                    // console.log(i + ': ' + o + ' => ' + n);
                    // console.log(o);
                    // console.log(n);
                }
                return n;
            }
            var newCrop = ff('ngCrop', newv[0], oldv[0]);
            var oldCrop = oldv[0];

            var newCoordinatrs = ff('ngCropCoordinates', newv[1], oldv[1]);
            var oldCoordinatrs = oldv[1];
            if (newCoordinatrs && oldCoordinatrs) {
                ff('ngCropCoordinates0', newCoordinatrs[0], oldCoordinatrs[0]);
                ff('ngCropCoordinates1', newCoordinatrs[1], oldCoordinatrs[1]);
                ff('ngCropCoordinates2', newCoordinatrs[2], oldCoordinatrs[2]);
                ff('ngCropCoordinates3', newCoordinatrs[3], oldCoordinatrs[3]);
            }
            var newDisabled = ff('ngCropDisabled', newv[3], oldv[3]);
            var newState = ff('ngCropState', newv[2], oldv[2]);
            if (!newCrop) {
                $scope.setNewImage('', true);
                $scope.setNewDisabled(true, true);
                $scope.setNewCoordinates(null, true);
                $scope.setNewLoading(true, true);
                $scope.onLoad('');
                $scope.redraw('image_loaded')
            }
            else if (newCrop !== $scope.url || !$scope.img) {
                var oldloading = $scope.loading;
                $scope.setNewLoading(true, true);
                var img = new Image();

                var err = function (e) {
                    $scope.setNewState($scope.state, true);
                    $scope.setNewImage($scope.url, true);
                    $scope.setNewDisabled($scope.disabled, true);
                    $scope.setNewCoordinates($scope.coordinates, true);
                    $scope.setNewLoading(oldloading, true);
                    $scope.onError(typeof e === 'string' ? e : 'image loading error');
                    $scope.redraw('image_failed');
                }

                img.onload = function () {
                    try {
                        var newLogic = new Logic(img, $scope.options, $scope.$container);
                        var old_image = $scope.img;
                        $scope.img = img;
                        $scope.setNewLogic(newLogic, true);
                        var new_state = $scope.logic.normalizeState(newState ? newState : $scope.logic.autoState());
                        $scope.setNewState(new_state, true);
                        if (!newCoordinatrs) {
                            $scope.rect = $scope.logic.autoRect();
                        }
                        else {
                            $scope.rect = $scope.logic.resizeRect($scope.logic.img2canvasRect(newCoordinatrs, new_state), new_state);
                        }

                        $scope.setNewImage(newCrop, true);
                        $scope.setNewDisabled(newDisabled, true);
                        $scope.setNewCoordinates($scope.logic.canvas2imgrect($scope.rect, new_state), true);
                        $scope.setNewLoading(false, true);
                        $scope.onLoad(newCrop);
                        $scope.redraw('image_loaded')
                    }
                    catch (e) {
                        err(e);
                    }
                };

                img.onerror = err;

                img.src = newCrop;
            }
            else {
                $scope.setNewState(newState ? newState : $scope.logic.autoState(), true);
                $scope.setNewDisabled(newDisabled, true);
                $scope.setNewCoordinates(newCoordinatrs, true);
                $scope.redraw('state or coord changed')
                // var new_state = $scope.state ? $scope.state : $scope.logic.autoState();
                // new_state['zoom'] = newZoom;
                // if (newv[1][0] !== newv[1][0] || newv[1][1] !== newv[1][1] || newv[1][2] !== newv[1][2] || newv[1][3] !== newv[1][3]) {
                //     $scope.rect = $scope.logic.resizeRect(newv[1], $scope.state);
                // }
            }
        });

        $scope.setNewLogic = function (newlogic, inthisdigest) {
            $scope.logic = newlogic;

            var f = function () {
                $scope.ngCropLogic = newlogic;
            }
            inthisdigest ? f() : $timeout(f)

        }

        $scope.setNewState = function (newstate, inthisdigest) {
            $scope.state = newstate;

            var f = function () {
                $scope.ngCropState = newstate;
            }
            inthisdigest ? f() : $timeout(f)

        }

        $scope.setNewImage = function (newImageUrl, inthisdigest) {
            $scope.url = newImageUrl;

            var f = function () {
                $scope.ngCrop = newImageUrl;
            }
            inthisdigest ? f() : $timeout(f)

        }

        $scope.setNewDisabled = function (newDisabled, inthisdigest) {
            $scope.disabled = newDisabled;
            var f = function () {
                $scope.ngCropDisabled = newDisabled;
            }
            inthisdigest ? f() : $timeout(f)

        }

        $scope.setNewLoading = function (newloding, inthisdigest) {
            $scope.loading = newloding;
            var f = function () {
                $scope.ngCropLoading = newloding;
            }
            inthisdigest ? f() : $timeout(f)

        }

        $scope.setNewCoordinates = function (coords, inthisdigest) {
            $scope.coordinates = coords;
            var f = function () {
                if (coords) {
                    if (!$scope.ngCropCoordinates) {
                        $scope.ngCropCoordinates = [0, 0, 0, 0];
                    }
                    $scope.ngCropCoordinates[0] = coords[0];
                    $scope.ngCropCoordinates[1] = coords[1];
                    $scope.ngCropCoordinates[2] = coords[2];
                    $scope.ngCropCoordinates[3] = coords[3];
                }
                else {
                    $scope.ngCropCoordinates = coords;
                }
            };

            inthisdigest ? f() : $timeout(f)

        }

        $scope.redraw = function (why) {
            // console.log(why);
            $scope.redrawNewImage();
            $scope.redrawNewState();
            $scope.redrawNewRect();
        }

        $scope.redrawNewRect = function () {
            if ($scope.loading) return;
            if ($scope.disabled) {
                $scope.$element_corners.hide();
                $scope.$element_action_move.hide();
                $scope.$element_action_set.hide();
                $scope.$img.css({
                    width: $scope.logic.ctr.image_size[0] * $scope.logic.ctr.min_zoom,
                    height: $scope.logic.ctr.image_size[1] * $scope.logic.ctr.min_zoom,
                    left: px(0),
                    top: px(0)
                });
            }
            else {
                var cr = $scope.rect;
                $scope.$element_corners.show();
                $scope.$element_action_move.show();
                $scope.$element_action_set.show();
                $scope.$element_corners.css({left: (cr[0] + cr[2]) / 2, top: (cr[1] + cr[3]) / 2});
                $scope.$element_corners_w.css({left: cr[0]});
                $scope.$element_corners_n.css({top: cr[1]});
                $scope.$element_corners_e.css({left: cr[2]});
                $scope.$element_corners_s.css({top: cr[3]});

                $scope.$element_action_move.css({
                    'left': px(cr[0]),
                    'top': px(cr[1]),
                    'width': px(cr[2] - cr[0]),
                    'height': px(cr[3] - cr[1]),
                    'background-size': px($scope.logic.img2canvasW($scope.logic.ctr.image_size[0], $scope.state)) + ' ' +
                    px($scope.logic.img2canvasH($scope.logic.ctr.image_size[1], $scope.state)),
                    'background-position': 'left ' + px(-cr[0] - $scope.state.x - 1) + ' top ' + px(-cr[1] - $scope.state.y - 1)
                });
            }
        };

        $scope.redrawNewState = function () {
            if ($scope.loading) {
                $scope.$canvas.hide();
                $scope.$loading.show();
            }
            else {
                $scope.$loading.hide();
                $scope.$canvas.show();
                if ($scope.disabled) return;
                var ctr = $scope.logic.ctr;
                var cr = $scope.rect;
                $scope.$img.css({
                    'left': px(-$scope.state.x),
                    'top': px(-$scope.state.y),
                    'width': px($scope.logic.img2canvasW($scope.logic.ctr.image_size[0], $scope.state)),
                    'height': px($scope.logic.img2canvasH($scope.logic.ctr.image_size[1], $scope.state))
                });
            }
        };


        $scope.redrawNewImage = function () {
            if ($scope.img) {
                $scope.$element_action_move.css('background-image', 'url(' + $scope.img.src + ')');
                $scope.$img.attr('src', $scope.img.src);

                var ctr = $scope.logic.ctr;

                $scope.$canvas.css({
                    'width': px(ctr.canvas[0]), 'height': px(ctr.canvas[1]),
                    'left': px(($scope.$container.width() - ctr.canvas[0]) / 2),
                    'top': px(($scope.$container.height() - ctr.canvas[1]) / 2)
                });

            }
        };

        $scope.mouseRelativeToCanvas = function (event) {
            var of = $scope.$element_action_set.offset();
            return [(event.pageX - of.left) + $(window).scrollLeft(), (event.pageY - of.top) + $(window).scrollTop()];
        };


        $scope.zoom_to = function (new_zoomratio) {
            var stick_margin = 0.01;
            var imagerect = $scope.coordinates;

            new_zoomratio = inRange(new_zoomratio, $scope.logic.ctr.min_zoom, $scope.logic.ctr.max_zoom);

            if ($scope.logic.relativeDeviation(new_zoomratio, $scope.logic.ctr.max_zoom) < stick_margin) new_zoomratio = $scope.logic.ctr.max_zoom;
            if ($scope.logic.relativeDeviation(new_zoomratio, $scope.logic.ctr.min_zoom) < stick_margin) new_zoomratio = $scope.logic.ctr.min_zoom;


            var newstate = {
                zoom: new_zoomratio,
                x: (new_zoomratio * $scope.logic.ctr.image_size[0] - $scope.logic.ctr.canvas[0]) / 2,
                y: (new_zoomratio * $scope.logic.ctr.image_size[1] - $scope.logic.ctr.canvas[1]) / 2
            };

            var canvasrect = $scope.logic.img2canvasRect(imagerect, newstate);
            $scope.setNewRect(canvasrect, newstate);

            return true;

        };

        $scope.zoom_by = function (zoom_multiplier) {

            var float_error = 0.000001;

            if ((zoom_multiplier >= 1. && $scope.logic.relativeDeviation($scope.state.zoom, $scope.logic.ctr.max_zoom) < float_error) ||
                (zoom_multiplier <= 1. && $scope.logic.relativeDeviation($scope.state.zoom, $scope.logic.ctr.min_zoom) < float_error)) {
                return false;
            }

            return $scope.zoom_to($scope.state.zoom * zoom_multiplier);
        };


        $scope.setNewRect = function (nr, state) {
            var newcr = $scope.logic.resizeRect(nr, state ? state : $scope.state);
            if (newcr) {
                if (state) $scope.setNewState(state);
                $scope.rect = newcr;
                $scope.setNewCoordinates($scope.logic.canvas2imgrect(newcr, $scope.state));
                $scope.redraw('new_rect');
                return newcr;
            }
            else {
                return false;
            }
        }


        $scope.addListeners = function () {

            var mm = function (e) {
                if ($scope.disabled || $scope.loading) {
                    return false;
                }
                if (!$scope.mouse_clicked) {
                    return false;
                }
                var act = $scope.mouse_clicked;
                var current = act[3];
                var mousenow = $scope.mouseRelativeToCanvas(e);
                var dxdy = [mousenow[0] - act[0], mousenow[1] - act[1]];
                var d = [0, 0, 0, 0];
                var compass = createCompass(0);
                var newcr = null;

                if (act[2] === 'set') {
                    if (!dxdy[0] || !dxdy[1]) return;
                    if (dxdy[0] >= 0) {
                        d[2] = inRange(dxdy[0], 1, $scope.logic.ctr.canvas[0] - current[0]);
                        compass['e'] = 1;
                    }
                    else {
                        d[0] = inRange(dxdy[0], -current[0], -1);
                        compass['w'] = 1;
                    }
                    if (dxdy[1] >= 0) {
                        d[3] = inRange(dxdy[1], 1, $scope.logic.ctr.canvas[1] - current[1]);
                        compass['s'] = 1;
                    }
                    else {
                        d[1] = inRange(dxdy[1], -current[1], -1);
                        compass['n'] = 1;
                    }

                    $scope.setNewRect($scope.logic.addDXDY(current, d));

                }
                else if (act[2] === 'move') {
                    d = [inRange(dxdy[0], -current[0], $scope.logic.ctr.canvas[0] - current[2]),
                        inRange(dxdy[1], -current[1], $scope.logic.ctr.canvas[1] - current[3])];

                    $scope.setNewRect($scope.logic.addDXDY(current, d));
                }
                else {
                    var w = current[0] - current[2];
                    var h = current[1] - current[3];

                    if (act[2].indexOf('w') > -1) {
                        d[0] = inRange(dxdy[0], -current[0], -w);
                        compass['w'] = 1;
                    }
                    else if (act[2].indexOf('e') > -1) {
                        d[2] = inRange(dxdy[0], w, $scope.logic.ctr.canvas[0] - current[2]);
                        compass['e'] = 1;
                    }
                    else {
                        compass['e'] = 0.5;
                        compass['w'] = 0.5;
                    }
                    if (act[2].indexOf('n') > -1) {
                        d[1] = inRange(dxdy[1], -current[1], -h);
                        compass['n'] = 1;
                    }
                    else if (act[2].indexOf('s') > -1) {
                        d[3] = inRange(dxdy[1], h, $scope.logic.ctr.canvas[1] - current[3]);
                        compass['s'] = 1;
                    }
                    else {
                        compass['s'] = 0.5;
                        compass['n'] = 0.5;
                    }
                    // console.log('scale', current, d, $scope.logic.addDXDY(current, d));
                    $scope.setNewRect($scope.logic.addDXDY(current, d));

                    e.preventDefault();
                }
            }

            var mouse_wheeel = function (event) {
                event.preventDefault();
                if ($scope.disabled || $scope.loading) {
                    return false;
                }

                var normalized;
                if (event.wheelDelta) {
                    normalized = (event.wheelDelta % 120 - 0) == -0 ? event.wheelDelta / 120 : event.wheelDelta / 12;
                } else {
                    var rawAmmount = event.deltaY ? event.deltaY : event.detail;
                    normalized = -(rawAmmount % 3 ? rawAmmount * 10 : rawAmmount / 3);
                }

                var new_center = $scope.mouseRelativeToCanvas(event);
                var ret = $scope.zoom_by((normalized == 1) ? 10 / 9 : 9 / 10, new_center);

            };


            $scope.$element_actions.on('mousedown', function (e) {
                var action = $(this).attr('ng-crop-action');
                var prevrect = $scope.rect;
                if (action === 'set') {
                    var pxpy = $scope.mouseRelativeToCanvas(e);
                    prevrect = [pxpy[0], pxpy[1], pxpy[0], pxpy[1]];
                }
                $scope.mouse_clicked = $scope.mouseRelativeToCanvas(e).concat([action, prevrect]);
                e.preventDefault();
            });

            $(window).on('mousemove', mm).on('mouseup', function (e) {
                mm(e);
                $scope.mouse_clicked = false;
            });

            window.addEventListener(('onwheel' in document ? 'wheel' : 'onmousewheel' in document ? 'mousewheel' : 'DOMMouseScroll'), mouse_wheeel);
        }

        $scope.addListeners();

    };


    // console.log(angular);

    angular.module('ngCrop', []).directive('ngCrop', function ($compile, $templateCache, $timeout, $q) {
        return {
            restrict: 'A',
            scope: {
                ngCrop: '=ngCrop',
                ngCropCoordinates: '=ngCropCoordinates',
                ngCropOptions: '=ngCropOptions',
                ngCropLogic: '=ngCropLogic',
                ngCropState: '=ngCropState',
                ngCropLoading: '=ngCropLoading',
                ngCropDisabled: '=ngCropDisabled',

                ngCropOnError: '&ngCropOnError',
                ngCropOnLoad: '&ngCropOnLoad',

            },
            link: function ($scope, element, attrs, model) {
                $scope.onError = function (message) {
                    if ($scope.ngCropOnError()) $scope.ngCropOnError()("" + message);
                    console.error(message);
                }
                $scope.onLoad = function () {
                    if ($scope.ngCropOnLoad()) $scope.ngCropOnLoad()("img loaded");
                    // console.log('img loaded');
                }
                compileTemplate($scope, $compile, element);
                collectElements($scope, element);
                cropLinkFunc($scope, $q, $timeout, element, attrs, model);

            }
        }
    })
})(this.angular);