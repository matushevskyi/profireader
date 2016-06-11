
(function (window, angular, $) {
    "use strict";
    angular.module('FileManagerApp').controller('FileManagerCtrl', ['$http',
        '$scope', '$translate', '$cookies', '$timeout', 'fileManagerConfig', 'item', 'Upload', 'fileNavigator', 'fileUploader','$q','$filter','$ok',
        function ($http, $scope, $translate, $cookies, $timeout, fileManagerConfig, Item, Upload, FileNavigator, fileUploader, $q, $filter, $ok) {
            angularControllerFunction('UserLoginController', 'set_selected_user_menu')('file_manager');
            $scope.config = fileManagerConfig;
            $scope.appName = fileManagerConfig.appName;
            $scope.path_profireader = 'http://profireader.com';
            $scope.orderProp = ['model.type', 'model.name'];
            $scope.query = '';
            $scope.rootdirs = library;
            $scope.last_visit_root = last_visit_root;
            $scope.last_root_id = last_root_id;
            $scope.$$translate = translates;
            $scope.temp = new Item();
            $scope.fileNavigator = new FileNavigator($scope.last_root_id? $scope.last_root_id:($scope.rootdirs[0]?$scope.rootdirs[0]['id']: ""), file_manager_called_for);
            $scope.fileUploader = fileUploader;
            $scope.uploadFileList = [];
            $scope.viewTemplate = $cookies.get('viewTemplate') || 'main-table.html';
            $scope.error = error;
            $scope.file_manager_called_for = file_manager_called_for;
            $scope.file_manager_on_action = file_manager_on_action;
            $scope.file_manager_default_action = file_manager_default_action;
            $scope.root_id = '';
            $scope.root_name = '';
            $scope.copy_file_id = '';
            $scope.cut_file_id = '';
            $scope.timer = false;
            $scope.name = '';
            $scope.upload_file_id = '';
            $scope.uploadingProgress = false;
            $scope.can_upload = false;
            $scope.last_visit = document.referrer;
            
            $scope._ = function(phrase){
                var args = [].slice.call(arguments);
                return pr_dictionary(args.shift(), args, '', $scope, $ok, 'FileManagerCtrl');
            };

            $scope.setTemplate = function (name) {
                $cookies.put('viewTemplate', name);
                $scope.viewTemplate = name;
            };
            
            $scope.changeRoot = function (root) {
                $scope.can_upload=root.can_upload;
                $cookies.put('last_root' ,root.id);
                $scope.root_name = root.name;
                $scope.fileNavigator.setRoot(root.id);
            };

            
            $scope.touch = function (item) {
                item = item instanceof Item ? item : new Item();
                item.revert && item.revert();
                $scope.temp = item;
            };

            $scope.smartClick = function (item) {
                if (item.isFolder()) {
                    return $scope.fileNavigator.folderClick(item);
                }
                if (item.isImage() || item.model.type === 'file_video') {
                    if ($scope.file_manager_default_action === 'choose') {
                        if($scope.file_manager_called_for === 'file_browse_image' && item.isImage()){
                            try {
                                eval($scope.file_manager_on_action['choose'] + '(item.model);');
                            }
                            catch (e) {

                            }
                        }else if($scope.file_manager_called_for === 'file_browse_media' && item.model.type === 'file_video') {
                            try {
                                eval($scope.file_manager_on_action['choose'] + '(item.model);');
                            }
                            catch (e) {

                            }
                        }
                    } else if(item.model.type !== 'file_video') {
                        try {
                            eval('item' + '.' + 'download' + '();');//$scope.file_manager_on_action[actionname] + '(item);');
                        }catch (e) {

                        }
                    }
               }else if((item.model.type !== 'dir' && item.model.type !== 'parent') && $scope.file_manager_default_action !== 'choose'){
                    try {
                        eval('item' + '.' + 'download' + '();');//$scope.file_manager_on_action[actionname] + '(item);');
                    }catch (e) {

                        }
                }
                if (item.isEditable()) {
                    item.getContent();
                    $scope.touch(item);
                    $('#edit').modal('show');
                    return;
                }
            };

            $scope.isInThisPath = function (path) {
                var currentPath = $scope.fileNavigator.currentPath.join('/');
                return currentPath.indexOf(path) !== -1;
            };

            $scope.edit = function (item) {
                item.edit(function () {
                    $('#edit').modal('hide');
                });
            };

            $scope.changePermissions = function (item) {
                item.changePermissions(function () {
                    $('#changepermissions').modal('hide');
                });
            };

            $scope.search = function (query) {
                if(query && query !== ''){
                   $scope.fileNavigator.search(query, $scope.fileNavigator.getCurrentFolder());
                }else{
                    if($scope.fileNavigator.is_search){
                       self.search_text = '';
                       $scope.fileNavigator.goTo(-1);
                    }
                }
            };

            $scope.cut = function (item) {
                $cookies.put('cut_file_id' , item.model.id);
                $cookies.put('copy_file_id' , '');
                $scope.cut_file_id = $cookies.get('cut_file_id');
                $scope.copy_file_id = $cookies.get('copy_file_id');
                item.cut(function () {
                    $scope.fileNavigator.refresh();
                });
            };

            $scope.copy = function (item) {
                $cookies.put('copy_file_id' , item.model.id);
                $cookies.put('cut_file_id' , '');
                $scope.cut_file_id = $cookies.get('cut_file_id');
                $scope.copy_file_id = $cookies.get('copy_file_id');
                item.copy(function () {
                    $scope.fileNavigator.refresh();
                });
            };

            $scope.time_out = function () {
                $scope.timer = true;
                $timeout(function () {
                    $scope.timer = false
                }, 2000);
            };
            
            $scope.paste = function (item) {
                if ($scope.copy_file_id !== '' && $scope.cut_file_id === '') {
                    item.tempModel.mode = 'copy';
                    item.tempModel.id = $scope.copy_file_id;
                    item.tempModel.error = $scope._('error_copy');
                } else if ($scope.copy_file_id == '' && $scope.cut_file_id != '') {
                    item.tempModel.mode = 'cut';
                    item.tempModel.id = $scope.cut_file_id;
                    item.tempModel.error = $scope._('error_cut');
                }
                item.tempModel.len = $scope.fileNavigator.fileList.length;
                item.tempModel.time_o = $scope.time_out();
                item.tempModel.folder_id = $scope.fileNavigator.getCurrentFolder();
                item.paste(function () {
                    $scope.fileNavigator.refresh();
                    $cookies.put('cut_file_id' , '');
                    $cookies.put('copy_file_id' , '');
                    $scope.cut_file_id = $cookies.get('cut_file_id');
                    $scope.copy_file_id = $cookies.get('copy_file_id');
                });
            };

            $scope.compress = function (item) {
                item.compress(function () {
                    item.success = true;
                    $scope.fileNavigator.refresh();
                }, function () {
                    item.success = false;
                });
            };

            $scope.extract = function (item) {
                item.extract(function () {
                    item.success = true;
                    $scope.fileNavigator.refresh();
                }, function () {
                    item.success = false;
                });
            };

            $scope.remove = function (item) {
                item.tempModel.error = $scope._('error_remove');
                item.remove(function () {
                    $scope.fileNavigator.refresh();
                    $('#remove').modal('hide');
                });

            };

            $scope.set_property = function (item) {
                if ($scope.fileNavigator.fileNameExists(item.tempModel.name) && item.tempModel.name.trim() !== item.model.name.trim()) {
                    item.error = $scope._('error_invalid_filename');
                    return false;
                }
                item.set_properties(function () {
                    $scope.fileNavigator.refresh();
                    $('#properties').modal('hide');
                });
            };


            $scope.createFolder = function (item) {
                var name = item.tempModel.name && item.tempModel.name.trim();
                item.tempModel.type = 'dir';
                item.tempModel.path = $scope.fileNavigator.currentPath;
                item.tempModel.root_id = $scope.fileNavigator.root_id;
                item.tempModel.folder_id = $scope.fileNavigator.getCurrentFolder();

                if (name && !$scope.fileNavigator.fileNameExists(name)) {
                    item.createFolder(function () {
                        $scope.fileNavigator.refresh();
                        $('#newfolder').modal('hide');
                    });
                } else {
                    $scope.temp.error = $scope._('error_invalid_filename');
                    return false;
                }
            };

            $scope.take_action = function (item, actionname, permitted) {
                $scope.modal = '';
                if(permitted !== true)
                    return false
                if ($scope.file_manager_on_action[actionname] !== '' && actionname === 'download') {
                    try {
                        eval('item' + '.' + actionname + '();');//$scope.file_manager_on_action[actionname] + '(item);');
                    }
                    catch (e) {
                        console.error('Error item.action() execution action=', actionname, e);
                    }
                } else if ($scope.file_manager_on_action[actionname] !== '' && actionname === 'choose') {
                    try {
                        eval($scope.file_manager_on_action[actionname] + '(item.model);');
                    }
                    catch (e) {
                        console.error('Error on filemanager caller side at action=', actionname, e);
                    }
                } else if ($scope.file_manager_on_action[actionname] !== '') {
                    eval('$scope.' + actionname.toString() + '(item)');//$scope.file_manager_on_action[actionname] + '(item);');
                }
            };

            $scope.auto_remove = function(list, folder){
                var data = {
                    'list':list,
                    'folder_id':folder
                };
                return $http.post(fileManagerConfig.auto_removeUrl, data).success(function(data) {
                    }).error(function(data) {
                        console.log('auto_remove_error')
                    })['finally'](function() {
                        self.inprocess = false;
                    });
            };

            $scope.showModal = function(){
                $scope.hide = false;
            };

            $scope.hideModal = function(){
                $scope.hide = true;
            };

            $scope.abort = function(){
                if($scope.uploadFileList.length>0){
                    if($scope.f){
                        $scope.f.upload.abort();
                        $scope.f.progress = 0;
                        $scope.auto_remove($scope.list_file_id, $scope.fileNavigator.getCurrentFolder());
                    }
                    $('#uploadfile').find('input[type=file], input[type=number], textarea').val('');
                }
            };

            $scope.uploading = function(list){
                if(list.length>0 && $scope.uploadingProgress === false){
                    $timeout(function () {
                            $scope.upl = true
                    }, 1000);
                }else{
                    $scope.upl = false
                }
                return $scope.upl
            };

            $scope.uploadUsingUpload = function () {
                $scope.uploadingProgress = true;
                var url = '/filemanager/send/' + $scope.fileNavigator.getCurrentFolder() + '/';
                var count = 0
                var total = 0
                $scope.list_file_id = []
                for(var i=0;i<$scope.uploadFileList.length;i++){
                    total += $scope.uploadFileList[i].size
                }
                var oldprogress = 0
                var uploading = function(file){
                    file.upload = Upload.upload({
                        url: url,
                        data: $scope.name,
                        resumeSizeUrl: '/filemanager/resumeupload/',
                        resumeChunkSize: $scope.config['chunkSize'],
                        ftype: file.type,
                        headers: {
                            'optional-header': 'header-value'
                        },
                        fields: {username: $scope.username},
                        file: file
                    });
                    $scope.f.upload.progress(function (evt) {
                        $scope.thisprogress = Math.min(100, parseInt(100.0 *
                            evt.loaded / total));
                        $scope.f.progress = Math.min(100, parseInt(100.0 *
                            evt.loaded / total)) + oldprogress;
                    }).success(function (data) {
                        $scope.list_file_id.push(data.file_id)
                        if(data.error){
                            $scope.fileNavigator.refresh();
                        }
                        count += 1;
                        oldprogress += $scope.thisprogress;
                        if($scope.uploadFileList[count]){
                            $scope.f = $scope.uploadFileList[count];
                            uploading($scope.uploadFileList[count])
                        }else {
                            close()
                        }
                    }).error(function (data) {
                        $scope.hide = false;
                        $scope.uploadingProgress = false;
                        $scope.thisprogress = 0
                        $scope.f.progress = 0;
                        var errorMsg =  $scope._('error_uploading_files');
                        //for(var i=0;i<$scope.uploadFileList.length;i++){
                        //    $scope.auto_remove($scope.uploadFileList[i].name, $scope.fileNavigator.getCurrentFolder());
                        //}
                        $scope.temp.error = errorMsg;
                        $timeout(function () {
                            $scope.temp.error = ''
                        }, 2000);

                    });
                }

                if ($scope.uploadFileList){
                    $scope.f = $scope.uploadFileList[count];
                    uploading($scope.uploadFileList[count])
                }

                var close = function(){
                    $scope.thisprogress = 0
                    $scope.hide = false;
                    $scope.uploadingProgress = false;
                    $scope.f.progress = 0;
                    $scope.fileNavigator.refresh();
                    $('#uploadfile').find('input[type=file]').val('');
                    $('#uploadfile').modal('hide');
                }
            };

            $scope.getQueryParam = function (param) {
                var found;
                window.location.search.substr(1).split("&").forEach(function (item) {
                    if (param === item.split("=")[0]) {
                        found = item.split("=")[1];
                        return false;
                    }
                });
                return found;
            };

            $scope.isDisable = function (actionname, len, type, permited) {

                var style;
                if (actionname === 'paste' && ($scope.copy_file_id != '' || $scope.cut_file_id != '') && type === 'parent') {
                    style = ''
                } else if (($scope.copy_file_id == '' && $scope.cut_file_id == '') && len < 2) {
                    style = 'cursor: default;pointer-events: none;color: gainsboro;'
                } else if ((actionname !== 'paste' && ($scope.copy_file_id != '' || $scope.cut_file_id != '')) && len < 2 || type === 'parent') {
                    style = 'cursor: default;pointer-events: none;color: gainsboro;'
                } else if (actionname === 'paste' && ($scope.copy_file_id == '' && $scope.cut_file_id == '')) {
                    style = 'cursor: default;pointer-events: none;color: gainsboro;'
                } else {
                    style = ''
                }
                if(($scope.file_manager_default_action === actionname && (type !== 'parent' && type !== 'dir')) && len > 2){
                    style += 'font-weight: bold;color:black'
                }
                if(($scope.file_manager_called_for === 'file_browse_media' && actionname === 'choose') && type !== 'file_video'){
                    style = 'cursor: default;pointer-events: none;color: gainsboro;'
                }else if(($scope.file_manager_called_for === 'file_browse_image' && actionname === 'choose') && type !== 'img'){
                    style = 'cursor: default;pointer-events: none;color: gainsboro;'
                }
                if(actionname === 'download' && type === 'file_video'){
                    style = 'cursor: default;pointer-events: none;color: gainsboro;'
                }
                return style
            };

            $scope.isModal = function (actionname) {
                if (actionname === 'rename' || actionname === 'remove' || actionname === 'properties') {
                    return true
                }
            };

            $scope.glyph = function (actionname) {
                if (actionname == 'rename') {
                    return 'edit'
                } else if (actionname == 'cut') {
                    return 'scissors'
                } else if (actionname == 'properties') {
                    return 'wrench'
                }else if(actionname == 'choose'){
                    return 'hand-up'
                } else {
                    return actionname
                }
            };

            $scope.err = function () {
                if ($scope.error == 'False' && $scope.rootdirs.length != 0) {
                    return false
                } else {
                    return true
                }
            };

            $scope.getTitle = function(name, id, limit){
                if($scope.fileNavigator.search_text){
                    var re = new RegExp($scope.fileNavigator.search_text, "gi");
                    name = name.length <= limit ? name: $filter('limitTo')(name, limit) + '...';
                    var result = name.match(re);
                    if(result){
                        var res =  name.replace(re, '<span style="color:red">' + result[0] + '</span>');
                        $('#highlightT_'+id).html(res);
                        return name;
                    }else {
                        return name;
                    }
                }else {
                    name = name.length <= limit ? name: $filter('limitTo')(name, limit) + '...';
                    return name
                }
            };

            $scope.changeRoots = function () {
                if (error == 'False') {
                    if($scope.last_visit_root && $scope.rootdirs){
                        for(var n = 0;n < $scope.rootdirs.length;n++){
                            if($scope.rootdirs[n]['name'] === $scope.last_visit_root){
                                $scope.changeRoot($scope.rootdirs[n]);
                            }
                        }
                    }else{
                        $scope.changeRoot($scope.rootdirs[0])
                    }
                } else {
                    $scope.changeRoot('')
                }
            };

            $scope.errMsg = $scope._("You do not belong to any company!");
            $scope.changeRoots();
            $scope.isWindows = $scope.getQueryParam('server') === 'Windows';

        }]);
})(window, angular, jQuery);
