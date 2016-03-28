'use strict';

var gulp = require('gulp');
var del = require('del');

var less = require('gulp-less-sourcemap');
var path = require('path');

// Vars
var src = 'bower_components/';
var dst = 'new/';

var watch = require('gulp-watch');
//var ext_replace = require('gulp-ext-replace');

// TODO: OZ by OZ: paths to less files in map files are css/css. that is why we need ./profapp/static/css/css -> /profapp/static/css symlink. fix it
gulp.task('less_compile', function () {
  gulp.src('./css/*.less')
    .pipe(less({
        sourceMap: {
            sourceMapRootpath: '/static/css' // Optional absolute or relative path to your LESS files
        }
    }))
//    .pipe(ext_replace('.css', '.less.css'))
    .pipe(gulp.dest('./css'));
});

gulp.task('clean', function (cb) {
//    del([
//        'filemanager/*',
//    ], cb);
});

gulp.task('install_filemanager', function () {
    return true;
    return gulp.src(src + 'filemanager/dist/*')
        .pipe(gulp.dest(dst + 'filemanager/'));
});

gulp.task('install_fileuploader', function () {
    return gulp.src(src + 'ng-file-upload/ng-file-upload.min.js')
        .pipe(gulp.dest(dst + 'fileuploader/'));
});

gulp.task('install_angular', function () {
    return gulp.src(src + 'angular/angular.min.js')
        .pipe(gulp.dest(dst + 'angular/'));
});

gulp.task('install_angular_translate', function () {
    return gulp.src(src + 'angular-translate/angular-translate.min.js')
        .pipe(gulp.dest(dst + 'angular/'));
});

gulp.task('install_angular_cookies', function () {
    return gulp.src(src + 'angular-cookies/angular-cookies.min.js')
        .pipe(gulp.dest(dst + 'angular/'));
});

gulp.task('install_angular_animate', function () {
    return gulp.src(src + 'angular-animate/angular-animate.min.js')
        .pipe(gulp.dest(dst + 'angular-animate/'));
});

gulp.task('install_angular_bootstrap', function () {
    return gulp.src([src + 'angular-bootstrap/ui-bootstrap.min.js', src + 'angular-bootstrap/ui-bootstrap-tpls.min.js', src + 'angular-bootstrap/ui-bootstrap.js', src + 'angular-bootstrap/ui-bootstrap-tpls.js'])
        .pipe(gulp.dest(dst + 'angular-bootstrap/'));
});

gulp.task('install_angular_ui_tinymce', function () {
    return gulp.src(src + 'angular-ui-tinymce/src/tinymce.js')
        .pipe(gulp.dest(dst + 'angular-ui-tinymce/'));
});


gulp.task('install_tinymce', function () {
    return gulp.src(src + 'tinymce-dist/tinymce.jquery.min.js')
        .pipe(gulp.dest(dst + 'tinymce/'));
});

gulp.task('install_angular_crop', function () {
    return gulp.src([src + 'ngImgCrop/compile/minified/*'])
        .pipe(gulp.dest(dst + 'angular-crop/'));
});

gulp.task('install_angular_xeditable', function () {
    return gulp.src([src + 'angular-xeditable/dist/css/xeditable.css', src + 'angular-xeditable/dist/js/xeditable.js'])
        .pipe(gulp.dest(dst + 'angular-xeditable/'));
});

gulp.task('install_cropper', function () {
    return gulp.src([src + 'cropper/dist/cropper.css', src + 'cropper/dist/cropper.js'])
        .pipe(gulp.dest(dst + 'cropper/'));
});

gulp.task('install_slider', function () {
    return gulp.src([src + 'angular-ui-slider/src/slider.js'])
        .pipe(gulp.dest(dst + 'angular-ui-slider/'));
});

gulp.task('install_bootstrap', function () {
    return gulp.src([src + 'bootstrap/dist/**/*'])
        .pipe(gulp.dest(dst + 'bootstrap/'));
});

gulp.task('less', ['less_compile'], function() {
    return gulp.watch('./css/*.less', ['less_compile']);
});


gulp.task('default', ['clean', 'install_fileuploader', 'install_angular', 'install_angular_translate', 'install_angular_cookies', 
'install_angular_ui_tinymce', 'install_tinymce', 'install_angular_bootstrap', 'install_angular_animate', 'install_cropper',
'install_slider','install_bootstrap', 'install_angular_crop']);

