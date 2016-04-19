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
            // '<canvas class="ng-crop-canvas"></canvas>' +
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

        // $scope.$img = $scope.$e('img');
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

        this.canvas2imgRect = function (canvasrect, state) {
            return canvasrect ? [
                this.canvas2imgX(canvasrect[0], state), this.canvas2imgY(canvasrect[1], state),
                this.canvas2imgX(canvasrect[2], state), this.canvas2imgY(canvasrect[3], state)] : null;
        };

        this.canvas2imgPoint = function (canvaspoint, state) {
            return canvaspoint ?
                [this.canvas2imgX(canvaspoint[0], state), this.canvas2imgY(canvaspoint[1], state)] : null;
        };

        this.img2canvasPoint = function (imgpoint, state) {
            return imgpoint ?
                [this.img2canvasX(imgpoint[0], state), this.img2canvasY(imgpoint[1], state)] : null;
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
            return [this.ctr.canvas[0] * 4 / 10., this.ctr.canvas[1] * 4 / 10., this.ctr.canvas[0] * 6 / 10., this.ctr.canvas[1] * 6 / 10.];
        }

        // this.scaleImgRect = function (img_rect, zoom_ratio, compass) {
        //     var oldcx = (img_rect[2] + img_rect[0]) / 2.;
        //     var oldcy = (img_rect[3] + img_rect[1]) / 2.;
        //     var nw = (img_rect[2] - img_rect[0]) * zoom_ratio;
        //     var nh = (img_rect[3] - img_rect[1]) * zoom_ratio;
        //     return [
        //         oldcx - nw * compass.w,
        //         oldcy - nh * compass.n,
        //         oldcx + nw * compass.e,
        //         oldcy + nh * compass.s]
        // }

        this.scaleRect = function (rect, zoom_ratio, compass) {
            var oldcx = (rect[2] + rect[0]) / 2.;
            var oldcy = (rect[3] + rect[1]) / 2.;
            var oldw = (rect[2] - rect[0]) / 1.;
            var oldh = (rect[3] - rect[1]) / 1.;
            var nw = oldw * zoom_ratio;
            var nh = oldh * zoom_ratio;
            var ret = [
                oldcx - oldw / 2. - (nw - oldw) / 2. * compass.w,
                oldcy - oldh / 2. - (nh - oldh) / 2. * compass.n,
                oldcx + oldw / 2. + (nw - oldw) / 2. * compass.e,
                oldcy + oldh / 2. + (nh - oldh) / 2. * compass.s];
            // console.log('scaleRect old center', oldcx, oldcy);
            // console.log('scaleRect old size', (rect[2] - rect[0]), (rect[3] - rect[1]));
            // console.log('scaleRect old rect', rect);
            // console.log('scaleRect zoom ratio, compass', zoom_ratio, compass);
            // console.log('scaleRect new center', (ret[2] + ret[0]) / 2, (ret[3] + ret[1]) / 2);
            // console.log('scaleRect new size', (ret[2] - ret[0]), (ret[3] - ret[1]));
            // console.log('scaleRect onew rect', ret);
            return ret;

        };


        this.fitByCanvasRect = function (canvasrect, state, compass) {
            // scale canvas rect by image constrains (min/max size, aspect) and canvas size
            var ret = [canvasrect[0], canvasrect[1], canvasrect[2], canvasrect[3]];
            var imgrect = this.canvas2imgRect(canvasrect, state);
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

            var ret = this.fitByCanvasRect(canvasrect, state, compass);
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
                ret = this.fitByCanvasRect(ret, compass, true);
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

        this.recalculateStateForNewZoom = function (new_zoom, relative_to_canvas_point, state) {
            // console.log(new_zoom, relative_to_canvas_point, state)
            var zoom_multiplier = new_zoom / state.zoom;
            if (relative_to_canvas_point) {
                relative_to_canvas_point = [relative_to_canvas_point[0] * 2, relative_to_canvas_point[1] * 2];
            }
            else {
                relative_to_canvas_point = [this.ctr.canvas[0], this.ctr.canvas[1]];
            }

            // console.log('zoom_by RELATIVE TO CANVAS POINT', relative_to_canvas_point);

            var float_error = 0.000001;

            if ((zoom_multiplier >= 1. && this.relativeDeviation(state.zoom, this.ctr.max_zoom) < float_error) ||
                (zoom_multiplier <= 1. && this.relativeDeviation(state.zoom, this.ctr.min_zoom) < float_error)) {
                return state;
            }

            var rect = [0, 0, this.ctr.canvas[0], this.ctr.canvas[1]];

            var compass = {
                'w': (relative_to_canvas_point[0] - rect[0]) / (rect[2] - rect[0]),
                'n': (relative_to_canvas_point[1] - rect[1]) / (rect[3] - rect[1])
            };
            compass['s'] = 1. - compass['n'];
            compass['e'] = 1. - compass['w'];

            // debugger;
            var current_fit_img_rect = this.canvas2imgRect(rect, state);
            var new_fit_img_rect = this.scaleRect(current_fit_img_rect, 1. / zoom_multiplier, compass);
            var new_canvas_origin = [new_fit_img_rect[0] * new_zoom, new_fit_img_rect[1] * new_zoom];

            var new_state = {
                zoom: new_zoom,
                x: new_canvas_origin[0],
                y: new_canvas_origin[1]
            };

            // console.log(new_state)

            return new_state;
            // );

        };

        this.normalizeState = function (newstate, oldstate) {

            var retstate = {zoom: newstate['zoom'] ? newstate['zoom'] : this.ctr.min_zoom};
            retstate.zoom = inRange(retstate.zoom, this.ctr.min_zoom, this.ctr.max_zoom);
            var maxorigin = [this.img2canvasW(this.ctr.image_size[0], retstate) - this.ctr.canvas[0],
                this.img2canvasH(this.ctr.image_size[1], retstate) - this.ctr.canvas[1]];

            if (newstate['x'] >= 0 && newstate['y'] >= 0) {
                retstate.x = newstate['x'];
                retstate.y = newstate['y'];
            }
            else {
                if (oldstate) {
                    var newzoomstate = this.recalculateStateForNewZoom(retstate.zoom, null, oldstate);
                    retstate.x = newzoomstate.x;
                    retstate.y = newzoomstate.y;
                }
                else {
                    retstate.x = 0;
                    retstate.y = 0;
                }


            }

            retstate.x = inRange(retstate.x, 0, maxorigin[0]);
            retstate.y = inRange(retstate.y, 0, maxorigin[1]);

            return retstate;

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
            $scope.canvas_zoom = null;
            $scope.url = null;
            $scope.logic = null;
            $scope.options = null;
            $scope.REDRAW_NEW_RECT = 'REDRAW_NEW_RECT';
            $scope.REDRAW_NEW_ZOOM = 'REDRAW_NEW_ZOOM';
            $scope.REDRAW_NEW_IMAGE = 'REDRAW_NEW_IMAGE';

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

                $timeout($scope.draw);

            });


            // 'ngCropDisabled',
            $scope.$watchGroup(['ngCrop', 'ngCropCoordinates', 'ngCropState', 'ngCropDisabled'], function (newv, oldv) {
                // console.log(newv, oldv);
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
                    $scope.redraw($scope.REDRAW_NEW_IMAGE, "empty image loaded");
                }
                else if (newCrop !== $scope.url || !$scope.img) {
                    var oldloading = $scope.loading;
                    $scope.setNewLoading(true, true);
                    $scope.redraw($scope.REDRAW_NEW_IMAGE, 'draw loading image')
                    var img = new Image();
                    img.setAttribute('crossOrigin', 'anonymous');

                    var err = function (e) {
                        console.error(e);
                        $scope.setNewState($scope.state, true);
                        $scope.setNewImage($scope.url, true);
                        $scope.setNewDisabled($scope.disabled, true);
                        $scope.setNewCoordinates($scope.coordinates, true);
                        $scope.setNewLoading(oldloading, true);
                        $scope.onError(typeof e === 'string' ? e : 'image loading error');
                        $scope.redraw($scope.REDRAW_NEW_IMAGE, 'image loading failed');
                    }

                    img.onload = function () {
                        try {
                            var newLogic = new Logic(img, $scope.options, $scope.$container);
                            var old_image = $scope.img;
                            $scope.img = img;
                            $scope.img.crossOrigin = "anonymous";
                            $scope.setNewLogic(newLogic, true);
                            var new_state = $scope.logic.normalizeState(newState ? newState : $scope.logic.autoState(), $scope.state);
                            $scope.setNewState(new_state, true);
                            if (!newCoordinatrs) {
                                $scope.rect = $scope.logic.autoRect();
                            }
                            else {
                                $scope.rect = $scope.logic.resizeRect($scope.logic.img2canvasRect(newCoordinatrs, new_state), new_state);
                            }

                            $scope.setNewImage(newCrop, true);
                            $scope.setNewDisabled(newDisabled, true);
                            $scope.setNewCoordinates($scope.logic.canvas2imgRect($scope.rect, new_state), true);
                            $scope.setNewLoading(false, true);
                            $scope.onLoad(newCrop);
                            $scope.redraw($scope.REDRAW_NEW_IMAGE, 'new image loaded')
                        }
                        catch (e) {
                            err(e);
                        }
                    };

                    img.onerror = err;
                    setTimeout(function () {
                        img.src = newCrop;
                    })

                }
                else {

                    $scope.setNewCoordinates(newCoordinatrs, true);
                    var what_to_redraw = $scope.REDRAW_NEW_RECT;
                    var new_state = $scope.logic.normalizeState(newState ? newState : $scope.logic.autoState(), $scope.state);
                    if (!$scope.state || $scope.state.zoom !== new_state.zoom) {
                        what_to_redraw = $scope.REDRAW_NEW_ZOOM;
                    }
                    $scope.setNewState(new_state, true);
                    $scope.setNewDisabled(newDisabled, true);

                    $scope.redraw(what_to_redraw, 'state or coord changed')

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
                    if (newstate) {
                        if (!$scope.ngCropState) {
                            $scope.ngCropState = {x: 0, y: 0, zoom: 1};
                        }
                        $scope.ngCropState['x'] = newstate['x']
                        $scope.ngCropState['y'] = newstate['y']
                        $scope.ngCropState['zoom'] = newstate['zoom']
                        // $scope.ngCropState = newstate;
                    }
                    else {
                        $scope.ngCropState = newstate;
                    }

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

            $scope.redrawNewImage = function () {
                if ($scope.img) {
                    // $scope.$element_action_move.css('background-image', 'url(' + $scope.img.src + ')');
                    // $scope.$img.attr('src', $scope.img.src);

                    var ctr = $scope.logic.ctr;

                    $scope.$element_action_set.css({
                        'width': px(ctr.canvas[0]), 'height': px(ctr.canvas[1]),
                        'left': "0px",
                        'top': "0px"
                        // 'left': px(($scope.$container.width() - ctr.canvas[0]) / 2),
                        // 'top': px(($scope.$container.height() - ctr.canvas[1]) / 2)
                    });

                    $scope.$canvas.css({
                        'width': px(ctr.canvas[0]), 'height': px(ctr.canvas[1]),
                        'left': px(($scope.$container.width() - ctr.canvas[0]) / 2),
                        'top': px(($scope.$container.height() - ctr.canvas[1]) / 2)
                    });
                    // $scope.$canvas[0].width = ctr.canvas[0];
                    // $scope.$canvas[0].height = ctr.canvas[1];

                }
            };

            $scope.redrawNewZoom = function () {
                if (!$scope.img) return null;
                var logic = $scope.logic;
                var state = $scope.state;


                if ($scope.loading) {
                    $scope.$canvas.hide();
                    $scope.$loading.show();
                }
                else {
                    $scope.$loading.hide();
                    $scope.$canvas.show();


                    $scope.canvas_zoom = document.createElement('canvas');
                    // $scope.canvas_zoom.crossOrigin="anonymous";
                    // $scope.$canvas[0].crossOrigin="anonymous";
                    $scope.canvas_zoom.width = logic.img2canvasW(logic.ctr.image_size[0], state);
                    $scope.canvas_zoom.height = logic.img2canvasH(logic.ctr.image_size[1], state);
                    $scope.canvas_zoom.getContext('2d').drawImage($scope.img, 0, 0, logic.ctr.image_size[0], logic.ctr.image_size[1],
                        0, 0, $scope.canvas_zoom.width, $scope.canvas_zoom.height);

                    $scope.$canvas.css({
                            'background-image': 'url(' + $scope.canvas_zoom.toDataURL("image/png") + ')',
                            'background-position': 'left ' + px(-state.x) + ' top ' + px(-state.y)
                        }
                    );

//     [0].getContext('2d').drawImage(
//     $scope.canvas_zoom, state.x, state.y, logic.ctr.canvas[0], logic.ctr.canvas[1],
//     0,0, logic.ctr.canvas[0], logic.ctr.canvas[1]
// );

                    if ($scope.disabled) return;

                    $scope.$element_action_move.css('background-image', 'url(' + $scope.canvas_zoom.toDataURL("image/png") + ')');
// var a  = $scope.$canvas[0]
// try {
//     var b = a.toDataURL("image/png");
//     console.log(b);
// }
// catch (e) {
//     console.log(e);
//     debugger;
// }


// $scope.$element_action_move.css('background-image', 'url(' +  + ')');
// $scope.$element_action_move.css('background-size', px(logic.img2canvasW(logic.ctr.image_size[0], state)) +
//     ' ' + px(logic.img2canvasH(logic.ctr.image_size[1], state)))
                }
            }

            $scope.redrawNewRect = function () {
                if ($scope.loading) return;

                var logic = $scope.logic;
                var state = $scope.state;

                if ($scope.disabled) {
                    $scope.$element_corners.hide();
                    $scope.$element_action_move.hide();
                    $scope.$element_action_set.hide();
                    // $scope.$img.css({
                    //     width: $scope.logic.ctr.image_size[0] * $scope.logic.ctr.min_zoom,
                    //     height: $scope.logic.ctr.image_size[1] * $scope.logic.ctr.min_zoom,
                    //     left: px(0),
                    //     top: px(0)
                    // });
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
                        'background-position': 'left ' + px(-cr[0] - $scope.state.x - 1) + ' top ' + px(-cr[1] - $scope.state.y - 1)
                    });

                    // console.log(cr[2] - cr[0], $scope.$element_action_move.width(0), $scope.$element_action_move[0].)


                    // $scope.$element_action_move[0].getContext('2d').drawImage($scope.canvas_zoom,
                    //     state.x + cr[0], state.y + cr[1], cr[2] - cr[0], cr[3] - cr[1],
                    //     0, 0, cr[2] - cr[0], cr[3] - cr[1]);


                }
            };

// $scope.createImgZoomOrigin = function (logic, state) {
//     if (!$scope.img) return null;
//     resize_canvas = document.createElement('canvas');
//     resize_canvas.width = logic.ctr.canvas[0];
//     resize_canvas.height = logic.ctr.canvas[1];
//     resize_canvas.getContext('2d').drawImage($scope.img, 0, 0, width, height);
//     $(image_target).attr('src', resize_canvas.toDataURL("image/png"));
//
// }

            $scope.redraw = function (what_to_redraw, why) {
                // console.log(what_to_redraw, why);

                if (what_to_redraw === $scope.REDRAW_NEW_IMAGE) {
                    $scope.redrawNewImage();
                }

                if (what_to_redraw === $scope.REDRAW_NEW_IMAGE || what_to_redraw === $scope.REDRAW_NEW_ZOOM) {
                    $scope.redrawNewZoom();
                }

                $scope.redrawNewRect();
            }


            $scope.mouseRelativeToCanvas = function (event) {
                var of = $scope.$element_action_set.offset();
                return [(event.pageX - of.left) + $(window).scrollLeft(), (event.pageY - of.top) + $(window).scrollTop()];
            };


            $scope.zoom_to = function (new_zoomratio, new_canvas_point) {

                // var imagerect = $scope.coordinates;

                // console.log(new_canvas_point[0], new_canvas_point[1]);

                var newstate =
                    $scope.logic.normalizeState(
                        {
                            zoom: new_zoomratio,
                            x: new_canvas_point[0],
                            y: new_canvas_point[1]
                        }, $scope.state
                    );

                var stick_margin = 0.01;

                if ($scope.logic.relativeDeviation(newstate.zoom, $scope.logic.ctr.max_zoom) < stick_margin) newstate.zoom = $scope.logic.ctr.max_zoom;
                if ($scope.logic.relativeDeviation(newstate.zoom, $scope.logic.ctr.min_zoom) < stick_margin) newstate.zoom = $scope.logic.ctr.min_zoom;


                // var canvasrect = $scope.logic.img2canvasRect(imagerect, newstate);
                // $scope.setNewState(newstate, true);
                $scope.setNewRect($scope.logic.img2canvasRect($scope.coordinates, newstate), newstate);
                // console.log('zoom_to', new_zoomratio, newstate);

                return true;

            };


            $scope.setNewRect = function (nr, state) {
                var newcr = $scope.logic.resizeRect(nr, state ? state : $scope.state);

                if (newcr) {
                    var what_to_redraw = $scope.REDRAW_NEW_RECT;
                    if (state) {
                        if (!$scope.state || $scope.state.zoom !== state.zoom) {
                            // console.log('redrawing zoom');
                            what_to_redraw = $scope.REDRAW_NEW_ZOOM;
                        }
                        $scope.setNewState(state, true);
                    }
                    $scope.rect = newcr;
                    $scope.setNewCoordinates($scope.logic.canvas2imgRect(newcr, $scope.state));
                    $scope.redraw(what_to_redraw, 'new rect');
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
                        var canvas_point = $scope.mouseRelativeToCanvas(event);
                        // canvas_point = [canvas_point[0] + $scope.state.x , canvas_point[1] + $scope.state.y];
                        // console.log('mouse position', canvas_point, $scope.logic.canvas2imgPoint(canvas_point, $scope.state));
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
                    if ($scope.disabled || $scope.loading || $scope.processing || !$scope.state) {
                        return false;
                    }
                    $scope.processing = true;
                    var normalized;

                    if (event.wheelDelta) {
                        normalized = (event.wheelDelta % 120 - 0) == -0 ? event.wheelDelta / 120 : event.wheelDelta / 12;
                    } else {
                        var rawAmmount = event.deltaY ? event.deltaY : event.detail;
                        normalized = -(rawAmmount % 3 ? rawAmmount * 10 : rawAmmount / 3);
                    }

                    var canvas_point = $scope.mouseRelativeToCanvas(event)
                    // canvas_point = [canvas_point[0] + $scope.state.x , canvas_point[1] + $scope.state.y];

                    var new_zoom = $scope.state.zoom * ((normalized > 0) ? 10 / 9 : 9 / 10);

                    var new_zoom_state = $scope.logic.recalculateStateForNewZoom(new_zoom, canvas_point, $scope.state);
                    $scope.zoom_to(new_zoom_state.zoom, [new_zoom_state.x, new_zoom_state.y]);
                    $scope.processing = false;

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

        }
        ;


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
})
(this.angular);