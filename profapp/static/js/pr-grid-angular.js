/**
 * Created by oles on 12/19/16.
 */


module.run(function ($rootScope, $ok, $sce, $uibModal, $sanitize, $timeout, $templateCache) {

    angular.extend($rootScope, {
        setGridExtarnals: function (gridApi) {
            var scope = this;
            scope.gridApi = gridApi;

            gridApi.grid['all_grid_data'] = {
                paginationOptions: {pageNumber: 1, pageSize: 1},
                filter: {},
                sort: {},
                editItem: {}
            };
            gridApi.grid.additionalDataForMS = {};
            gridApi.grid.all_grid_data.paginationOptions.pageSize = gridApi.grid.options.paginationPageSize;
            var col = gridApi.grid.options.columnDefs;
            $.each(col, function (ind, c) {
                col[ind] = $.extend({
                    enableSorting: false,
                    enableFiltering: c['filter'] ? true : false,
                    displayName: c['displayName'] ? c['displayName'] : (c['name'].replace(".", ' ') + ' grid column name')
                }, c);
            });


            gridApi.grid.options.headerTemplate = '<div class="ui-grid-header" ><div class="ui-grid-top-panel"><div class="ui-grid-header-viewport"><div class="ui-grid-header"></div><div id="ui-grid-to-height" class="ui-grid-header-canvas">' +
                '<div class="ui-grid-header-cell-wrapper" ng-style="colContainer.headerCellWrapperStyle()"><div role="row" class="ui-grid-header-cell-row">' +
                '<div class="ui-grid-header-cell ui-grid-clearfix ui-grid-category" ng-repeat="cat in grid.options.category" ng-if="cat.visible && (colContainer.renderedColumns | filter:{ colDef:{category: cat.name} }).length > 0"> ' +
                '<div class="ui-grid-filter-container"><input type="text" class="form-control" ng-enter="grid.searchItemGrid(cat)" ng-model="cat.filter.text" aria-label="{{colFilter.ariaLabel || aria.defaultFilterLabel}}" placeholder="{{ grid.appScope._(\'search\') }}"> ' +
                '<div role="button" class="ui-grid-filter-button" ng-click="grid.refreshGrid(cat)" ng-if="!colFilter.disableCancelFilterButton" ng-disabled="cat.filter.text === undefined || cat.filter.text === null || cat.filter.text === \'\'" ng-show="cat.filter.text !== undefined && cat.filter.text !== null && cat.filter.text !== \'\'"> <i class="ui-grid-icon-cancel" ui-grid-one-bind-aria-label="aria.removeFilter">&nbsp;</i> </div> </div> ' +
                '<div class="ui-grid-header-cell ui-grid-clearfix" ng-if="col.colDef.category === cat.name && grid.options.category" ng-repeat="col in colContainer.renderedColumns | filter:{ colDef:{category: cat.name} }" ui-grid-header-cell col="col" render-index="$index"> <div ng-class="{ \'sortable\': sortable }" class="ng-scope sortable"> <div ui-grid-filter="" ng-show="col.colDef.category !== undefined"></div> </div> </div> </div>' +
                '<div class="ui-grid-header-cell ui-grid-clearfix" ng-if="col.colDef.category === undefined || grid.options.category === undefined"  ng-repeat="col in colContainer.renderedColumns track by col.colDef.name" ui-grid-header-cell col="col" render-index="$index" ng-style="$index === 0 && colContainer.columnStyle($index)"></div>' +
                '</div></div></div></div></div></div>';

            for (var i = 0; i < col.length; i++) {
                if (col[i].category) {
                    gridApi.grid.options.columnDefs[i].enableFiltering = false
                }
                gridApi.grid.options.columnDefs[i].headerCellTemplate = '<div ng-class="{ \'sortable\': sortable }">' +
                    '<div class="ui-grid-cell-contents" col-index="renderIndex" title="{{ grid.appScope._(col.displayName CUSTOM_FILTERS) }}"> <span>{{ grid.appScope._(col.displayName CUSTOM_FILTERS) }}</span>' +
                    '<span ui-grid-visible="col.sort.direction" ng-class="{ \'ui-grid-icon-up-dir\': col.sort.direction == asc, \'ui-grid-icon-down-dir\': col.sort.direction == desc, \'ui-grid-icon-blank\': !col.sort.direction }"> &nbsp;</span> </div> <div class="ui-grid-column-menu-button" ng-if="grid.options.enableColumnMenus && !col.isRowHeader  && col.colDef.enableColumnMenu !== false" ng-click="toggleMenu($event)" ng-class="{\'ui-grid-column-menu-button-last-col\': isLastCol}">' +
                    ' <i class="ui-grid-icon-angle-down">&nbsp;</i> </div> <div ui-grid-filter></div></div>';

                function generateFilterTemplate(col) {
                    switch (col.filter.type) {
                        case 'input':
                            return '<div class="ui-grid-filter-container">' +
                                '<input type="text" class="form-control" ng-enter="grid.searchItemGrid(col)" ng-model="col.filter.text"  aria-label="{{colFilter.ariaLabel || aria.defaultFilterLabel}}">' +
                                '<div role="button" class="ui-grid-filter-button" ng-click="grid.refreshGrid(col)" ng-if="!colFilter.disableCancelFilterButton" ng-disabled="col.filter.text === undefined || col.filter.text === null || col.filter.text === \'\'" ng-show="col.filter.text !== undefined && col.filter.text !== null && col.filter.text !== \'\'">' +
                                '<i class="ui-grid-icon-cancel" ui-grid-one-bind-aria-label="aria.removeFilter">&nbsp;</i></div></div>'
                        case 'date_range':
                            return '<div class="ui-grid-filter-container" style="position: fixed; top:auto; left: auto; width: 25%;cursor: pointer;z-index: 1"><input placeholder="from"  style="width: 48%; display: inline;" class="form-control" pr-date-picker ng-model="col.filters[0].term" ng-required="true" close-text="Close"/>' +
                                '<input style="width: 48%; display: inline;" class="form-control" pr-date-picker ng-model="col.filters[1].term" ng-required="true" placeholder="to"  close-text="Close"/>' +
                                '<span class="input-group-btn"></span><div role="button" class="ui-grid-filter-button" ng-click="grid.refreshGrid(col)" ng-if="!colFilter.disableCancelFilterButton" ng-disabled="col.filters[1].term === undefined || col.filters[0].term === undefined" ng-show="col.filters[1].term !== undefined && col.filters[1].term !== \'\' && col.filters[0].term !== undefined && col.filters[0].term !== \'\'">' +
                                '<i class="ui-grid-icon-cancel" ui-grid-one-bind-aria-label="aria.removeFilter" style="right:0.5px;">&nbsp;</i></div></div>'
                        case 'multi_select':
                            return '<div class="ui-grid-filter-container"><div ng-dropdown-multiselect="" parent-scope="grid.appScope" data="grid.all_grid_data" add-data="grid.additionalDataForMS[col.name]" send="grid.setGridData" options = "grid.listsForMS[col.name]" selected-model="grid.listOfSelectedFilterGrid"></div></div>'
                        case 'range':
                            return '<div class="ui-grid-filter-container">' +
                                '<input type="number" class="form-control"  ng-model="col.filters[0].term"  aria-label="{{colFilter.ariaLabel || aria.defaultFilterLabel}}" style="margin-bottom: 10px;width: 100%" placeholder="From:">' +
                                '<input type="number" class="form-control"  ng-model="col.filters[1].term"  aria-label="{{colFilter.ariaLabel || aria.defaultFilterLabel}}" style="margin-bottom: 5px;width: 100%" placeholder="To:">' +
                                '<button class="btn btn-group" ng-click="grid.filterForGridRange(col)" ng-disabled="col.filters[1].term === undefined || col.filters[0].term === undefined || col.filters[1].term === null || col.filters[1].term === \'\' || col.filters[0].term === null || col.filters[0].term === \'\'">Filter</button> ' +
                                '<div role="button" class="ui-grid-filter-button" ng-click="grid.refreshGrid(col)" ng-if="!colFilter.disableCancelFilterButton" ng-disabled="col.filters[1].term === undefined || col.filters[0].term === undefined" ng-show="col.filters[1].term !== undefined && col.filters[1].term !== \'\' && col.filters[0].term !== undefined && col.filters[0].term !== \'\'">' +
                                '<i class="ui-grid-icon-cancel" ui-grid-one-bind-aria-label="aria.removeFilter" style="right:0.5px;top:83%">&nbsp;</i></div></div>'
                        case 'button':
                            return '<div class="ui-grid-filter-container" ng-if="grid.filters_action.' + col.name + '"><button ' +
                                ' class="btn pr-grid-cell-field-type-actions-action pr-grid-cell-field-type-actions-action-{{ grid.filters_action.' + col.name + ' }}" ' +
                                ' ng-click="grid.appScope.' + col.filter.onclick + '(row.entity.id,  grid.filters_action.' + col.name + ' , row.entity, \'' + col['name'] + '\')" ' +
                                ' title="{{ grid.filters_action.' + col.name + ' }}" ng-bind="grid.filters_action.' + col.name + '"></button><span class="grid-filter-info" ng-bind="grid.filters_info.' + col.name + '"></span></div>'
                    }
                }


                function generateCellTemplate(col, columnindex) {
                    var classes_for_row = ' ui-grid-cell-contents pr-grid-cell-field-type-' +
                        (col.type ? col.type : 'text') + ' pr-grid-cell-field-name-' + col.name.replace(/\./g, '-') + ' ' + (typeof col.classes === 'string' ? col.classes : '') + '';
                    if (typeof  col.classes === 'function') {
                        classes_for_row += '{{ grid.options.columnDefs[' + columnindex + '].classes(row.entity.id, row.entity, col.field) }} ';
                    }

                    var cell_raw_value = 'COL_FIELD';
                    if (col['render']) {
                        cell_raw_value = 'grid.options.columnDefs[' + i + '][\'render\'](row.entity, COL_FIELD)';
                    }

                    var attributes_for_cell = +col.name + '" pr-id="{{ row.entity.id }}" ';
                    var cell_title = 'title = "{{ ' + cell_raw_value + '|strip_html }}"';
                    if (col['uib-tooltip-html']) {
                        attributes_for_cell += ' aatooltip-popup-close-delay="100000" tooltip-append-to-body="true" tooltip-class="pr-grid-tooltip-class" tooltip-animation="false" uib-tooltip-html="' + 'grid.options.columnDefs[' + i + '][\'uib-tooltip-html\'](row.entity, COL_FIELD)' + '" ';
                        cell_title = '';
                    }


                    var onclickdisable = gridApi.grid.options['disableByField'] ? 'grid.onclick_is_disabled(row.entity[\'' + gridApi.grid.options['disableByField'] + '\']) && ' : '';
                    if (col.onclick) {
                        if (col.type === 'actions') {
                            col.onclick = onclickdisable + 'grid.appScope.' + col['onclick'] + '(row.entity.id, \'{{ action_name }}\', row.entity, \'' + col['name'] + '\')';
                        }
                        else if (col.type === 'change_status') {
                            col.onclick = onclickdisable + 'grid.appScope.' + col['onclick'] + '(row.entity.id, new_status_and_enabled[\'status\'], row.entity, \'' + col['name'] + '\')';
                        }
                        else if (col.type === 'icons') {
                            attributes_for_cell += ' ng-click="' + onclickdisable + 'grid.onclick_without_bubbling($event, grid.appScope.' + col.onclick + ', row.entity.id, undefined, row.entity, \'' + col['name'] + '\')"';
                            classes_for_row += ' link '
                        }
                        else if (col.type !== 'editable') {
                            attributes_for_cell += ' ng-click="' + onclickdisable + 'grid.appScope.' + col.onclick + '(row.entity.id, row.entity, \'' + col['name'] + '\')"';
                            classes_for_row += ' link '
                        }

                    }


                    var cell_value = '{{ ::' + cell_raw_value + ' }}';
                    var cell_html_value = '<span ng-bind-html="' + cell_raw_value + '"></span>';


                    var prefix_img = '';
                    if (col.img_url) {
                        var prefix_img = '<img src="' + static_address('images/0.gif') + '" class="pr-grid-cell-img-prefix" style="background-size: contain; background-repeat: no-repeat; background-position: center center; background-color: #fff; background-image: url({{ row.entity.' + col.img_url + ' }})" />';
                    }
                    switch (col.type) {
                        case 'link':
                            return '<div  ' + attributes_for_cell + ' ng-style="grid.appScope.' + col.cellStyle + '" class="' + classes_for_row + '" ' + cell_title + '">' + prefix_img + '<a ng-style="grid.appScope.' + col.cellStyle + '"' + attributes_for_cell + ' ' + (col.target ? (' target="' + col.target + '" ') : '') + ' href="{{' + 'grid.appScope.' + col.href + '}}">' + cell_value + '<i ng-if="' + col.link + '" class="fa fa-external-link ml05em" style="font-size: 12px"></i></a></div>';
                        case 'img':
                            return '<div  ' + attributes_for_cell + '  class="' + classes_for_row + '">' + prefix_img + '<img ng-src="' + cell_value + '" style="background-position: center; height: 30px;text-align: center; background-repeat: no-repeat;background-size: contain;"></div>';
                        case 'tags':
                            return '<div  ' + attributes_for_cell + '  class="' + classes_for_row + '">' + prefix_img + '<span ng-repeat="tag in ' + cell_raw_value + '"' +
                                ' class="m025em label label-danger">{{ tag.text }}</span></div>';
                        case 'show_modal':
                            return '<div  ' + attributes_for_cell + '  class="' + classes_for_row + '" ' + cell_title + '">' + prefix_img + '<a ng-click="' + col.modal + '">' + cell_value + '</a></div>';
                        case 'actions':
                            return '<div  ' + attributes_for_cell + '  class="' + classes_for_row + '">' + prefix_img + '<button ' +
                                ' class="btn pr-grid-cell-field-type-actions pr-grid-cell-field-type-actions-action-{{ action_name }}" ' +
                                ' ng-repeat="(action_name, enabled) in ' + cell_raw_value + '" ng-disabled="enabled !== true" ng-style="{width:grid.getLengthOfAssociativeArray(' + cell_value + ')>3?\'2.5em\':\'5em\'}"' +
                                ' ng-click="' + onclickdisable + col.onclick + '" ' +
                                ' title="{{ grid.appScope._((enabled === true)?(action_name + \' grid action\'):enabled) }}">{{ grid.appScope._(action_name + \' grid action\') }}</button></div>';
                        // case 'change_status':
                        //     return '<div  ' + attributes_for_cell + '  class="' + classes_for_row + '">' + prefix_img + '<button ' +
                        //         ' class="btn pr-grid-cell-field-type-change_status pr-grid-cell-field-type-change_status-old-{{ row.entity[\''+col['old_status_column_name']+'\'] }} pr-grid-cell-field-type-change_status-new-{{ new_status }}" ' +
                        //         ' ng-repeat="new_status_and_enabled in ' + cell_raw_value + '" ng-disabled="new_status_and_enabled[\'enabled\'] !== true"' +
                        //         ' ng-click="' + col.onclick + '" ' +
                        //         ' title="{{ grid.appScope._((new_status_and_enabled[\'enabled\'] === true)?(\'change \' + row.entity[\''+col['old_status_column_name']+'\'] + \' to \' + new_status_and_enabled[\'status\']):new_status_and_enabled[\'enabled\']) }}">{{ grid.appScope._(row.entity[\'' + col['old_status_column_name'] + '\'] + \'=>\' + new_status_and_enabled[\'status\'], null, \'make \' + new_status_and_enabled[\'status\']) }}</button></div>';
                        case 'icons':
                            return '<div  ' + attributes_for_cell + '  class="' + classes_for_row + '">' + prefix_img + '<i ng-class="{disabled: !icon_enabled}" ' +
                                'class="pr-grid-cell-field-type-icons-icon pr-grid-cell-field-type-icons-icon-{{ icon_name }}" ng-repeat="(icon_name, icon_enabled) in ' + cell_raw_value + '" ng-click="' + onclickdisable + 'grid.onclick_without_bubbling($event, grid.appScope.' + col.onclick + ', row.entity.id, \'{{ icon_name }}\', row.entity, \'' + col['name'] + '\')" title="{{ grid.appScope._(\'grid icon \' + icon_name) }}"></i></div>';
                        case 'editable':
                            if (col.multiple === true && col.rule) {
                                return '<div  ' + attributes_for_cell + '  class="' + classes_for_row + '" ng-if="grid.appScope.' + col.rule + '=== false" ' + cell_title + '">' + prefix_img + '' + cell_value + '</div><div ng-if="grid.appScope.' + col.rule + '"><div ng-click="' + onclickdisable + col.modal + '" ' + cell_title + '" id=\'grid_{{row.entity.id}}\'>' + cell_value + '</div></div>';
                            }
                            if (col.subtype && col.subtype === 'tinymce') {
                                return '<div  ' + attributes_for_cell + '  class="' + classes_for_row + '" ng-click="' + onclickdisable + col.modal + '" ' + cell_title + '" id=\'grid_{{row.entity.id}}\'>' + prefix_img + '' + cell_value + '</div>';
                            }
                        default:
                            return '<div  ' + attributes_for_cell + '  class="' + classes_for_row + '" ' + cell_title + '">' + prefix_img + '' + cell_html_value + '</div>';

                    }
                }

                if (col[i].filter) {
                    if (col[i].filter.type === 'date_range') {
                        gridApi.grid.options.columnDefs[i].filters = [{}, {}];
                        gridApi.grid.options.columnDefs[i].width = '25%';
                    } else if (col[i].filter.type === 'multi_select') {
                        gridApi.grid.listOfSelectedFilterGrid = [];
                        gridApi.grid.additionalDataForMS[col[i].name] = {
                            limit: col[i].filter.limit ? col[i].filter.limit : null,
                            type: col[i].filter.type,
                            field: col[i].name
                        };
                    } else if (col[i].filter.type === 'range') {
                        gridApi.grid.options.columnDefs[i].filters = [{}, {}];
                    }
                    gridApi.grid.options.columnDefs[i].filterHeaderTemplate = generateFilterTemplate(col[i]);
                }


                gridApi.grid.options.columnDefs[i].cellTemplate = generateCellTemplate(col[i], i);

            }

            gridApi.grid['getLengthOfAssociativeArray'] = function (array) {
                return Object.keys(array).length
            };

            gridApi.grid['onclick_is_disabled'] = function (disabled) {
                console.log(disabled);
                return disabled ? false : true;
            };

            gridApi.grid['onclick_without_bubbling'] = function () {
                var args = Array.prototype.slice.call(arguments);
                var $event = args.shift();
                var func = args.shift();
                if ($event.stopPropagation) $event.stopPropagation();
                if ($event.preventDefault) $event.preventDefault();
                $event.cancelBubble = true;
                $event.returnValue = false;
                return func ? func.apply(this, args) : null;
            };

            gridApi.grid['searchItemGrid'] = function (col) {
                //highLightSubstring(col.filter.text, 'ui-grid-canvas',col.field)
                gridApi.grid.all_grid_data.paginationOptions.pageNumber = 1;
                gridApi.grid.all_grid_data['filter'][col.field] = col.filter.text;
                gridApi.grid.setGridData()
            };

            gridApi.grid['grid_change_row'] = function (new_row) {
                $.each(gridApi.grid.options.data, function (index, old_row) {
                    if (old_row['id'] && old_row['id'] === new_row['id']) {
                        if (new_row.hasOwnProperty('replace_id')) {
                            new_row['id'] = new_row['replace_id']
                        }
                        gridApi.grid.options.data[index] = new_row;
                    }
                });
            };

            gridApi.grid['set_data_function'] = function (grid_data) {
                for (var i = 0; i < gridApi.grid.options.columnDefs.length; i++) {
                    if (gridApi.grid.options.columnDefs[i]['alias_for']) {
                        for (var j = 0; j < grid_data.grid_data.length; j++) {
                            grid_data.grid_data[j][gridApi.grid.options.columnDefs[i]['name']] = grid_data.grid_data[j][gridApi.grid.options.columnDefs[i]['alias_for']];
                        }
                    }
                }
                gridApi.grid.options.data = grid_data.grid_data;
                gridApi.grid.filters_init_exception = grid_data.grid_filters_except
                gridApi.grid.listsForMS = {};
                gridApi.grid.options.totalItems = grid_data.total;
                if (grid_data.page) {
                    gridApi.grid.options.pageNumber = grid_data.page;
                    gridApi.grid.options.paginationCurrentPage = grid_data.page;
                }
                $timeout(function () {
                    $(".ui-grid-filter-select option[value='']").remove();
                }, 0);
                for (var i = 0; i < col.length; i++) {
                    if (col[i].filter) {
                        if (col[i].filter.type === 'select') {
                            gridApi.grid.options.columnDefs[i]['filter']['selectOptions'] = grid_data.grid_filters[col[i].name]
                        } else if (col[i].filter.type === 'multi_select') {
                            gridApi.grid.options.columnDefs[i]['filter']['selectOptions'] = grid_data.grid_filters[col[i].name];
                            gridApi.grid.listsForMS[col[i].name] = grid_data.grid_filters[col[i].name].slice(1);
                        }
                    }
                }
                for (var m = 0; m < grid_data.grid_data.length; m++) {
                    if (grid_data.grid_data[m]['level'])
                        grid_data.grid_data[m].$$treeLevel = 0
                }
                if (gridApi.grid.all_grid_data) {
                    gridApi.grid.all_grid_data['editItem'] = {};
                }
            }

            gridApi.grid['setGridData'] = function (grid_data) {
                var all_grid_data = grid_data ? grid_data : gridApi.grid.all_grid_data
                if (gridApi.grid.options.urlLoadGridData) {
                    scope.loading = true;
                    $ok(gridApi.grid.options.urlLoadGridData, all_grid_data, function (grid_data) {
                        gridApi.grid.set_data_function(grid_data)
                    }).finally(function () {
                        scope.loading = false
                    })
                } else {
                    gridApi.grid.options.loadGridData(all_grid_data, function (grid_data) {
                        gridApi.grid.set_data_function(grid_data)
                    })
                }

            };


            if (!gridApi.grid.load_contr) {
                gridApi.grid.load_contr = true;
                gridApi.grid.setGridData()
            }


            gridApi.grid['filterForGridRange'] = function (col) {
                from = col.filters[0]['term'];
                to = col.filters[1]['term'];
                gridApi.grid.all_grid_data['filter'][col.field] = {'from': from, 'to': to};
                gridApi.grid.setGridData();
            };

            gridApi.grid['refreshGrid'] = function (col) {
                if (col !== undefined) {
                    if (col.filters && (col.filter.type === 'date_range' || col.filter.type === 'range')) {
                        col.filters[0] = '';
                        col.filters[1] = '';
                    } else if (col.filter.type === 'input') {
                        col.filter.text = '';
                    }
                    delete gridApi.grid.all_grid_data['filter'][col.field];
                    gridApi.grid.setGridData()
                }
            };


            gridApi.grid['pr_take_action'] = function (id, action, row) {
                console.log('pr_take_action', id, action, row);
            };

            gridApi.grid['pr_build_actions_buttons'] = function (id, actions, row) {
                var ret =
                    $sce.trustAsHtml(_.map(actions, function (action) {
                        return '<button ng-click="grid.appScope.pr_take_action(row.entity.id, \'' + action + '\', row.entity)">' + action + '</button>'
                    }).join('&nbsp;'));

                return ret;
                //console.log('pr_build_actions_buttons', id, actions, row);
            };

            gridApi.core.on.sortChanged(scope, function (grid, sortColumns) {
                gridApi.grid.all_grid_data['sort'] = {};
                if (sortColumns.length !== 0) {
                    gridApi.grid.all_grid_data['sort'][sortColumns[0].field] = sortColumns[0].sort.direction;
                }
                gridApi.grid.setGridData()
            });

            if (gridApi.edit) gridApi.edit.on.afterCellEdit(scope, function (rowEntity, colDef, newValue, oldValue) {
                if (newValue !== oldValue) {
                    gridApi.grid.all_grid_data['editItem'] = {
                        'name': rowEntity.name,
                        'newValue': newValue,
                        'template': rowEntity.template,
                        'col': colDef.name
                    };
                    gridApi.grid.all_grid_data.paginationOptions.pageNumber = 1;
                    gridApi.grid.setGridData()
                }
            });

            if (gridApi.grid.options.paginationTemplate) {
                gridApi.pagination.on.paginationChanged(scope, function (newPage, pageSize) {
                    gridApi.grid.all_grid_data.paginationOptions.pageNumber = newPage;
                    gridApi.grid.all_grid_data.paginationOptions.pageSize = pageSize;
                    $timeout(function () {
                        gridApi.grid.setGridData()
                    }, 500)

                });
            }

            gridApi.core.on.filterChanged(scope, function () {
                var grid = this.grid;
                var at_least_one_filter_changed = false;
                for (var i = 0; i < grid.columns.length; i++) {

                    var term = grid.columns[i].filter.term;
                    var type = grid.columns[i].filter.type;
                    var field = grid.columns[i].name;

                    if (type === 'date_range') {
                        if (grid.columns[i].filters[0].term && grid.columns[i].filters[1].term) {
                            at_least_one_filter_changed = true;
                            var offset = new Date().getTimezoneOffset();
                            var from = new Date(grid.columns[i].filters[0].term).getTime();
                            var to = new Date(grid.columns[i].filters[1].term).getTime();
                            var error = from - to >= 0;
                            gridApi.grid.all_grid_data['filter'][field] = {
                                'from': from - (offset * 60000),
                                'to': to - (offset * 60000)
                            };
                        }
                    } else if (term !== undefined) {
                        if (term !== gridApi.grid.all_grid_data['filter'][field]) {
                            at_least_one_filter_changed = true;
                            term != null ? gridApi.grid.all_grid_data['filter'][field] = term : delete gridApi.grid.all_grid_data['filter'][field]
                        }
                    }
                }
                if (at_least_one_filter_changed) {
                    error ? add_message('You push wrong date', 'danger', 3000) : gridApi.grid.setGridData()
                }
            });

            if (gridApi.grid.options.enableRowSelection) {
                gridApi.selection.on.rowSelectionChanged(scope, function (row) {
                    scope.list_select = gridApi.selection.getSelectedRows();
                    scope.isSelectedRows = gridApi.selection.getSelectedRows().length !== 0;
                });
            }
        },
        gridOptions: {
            onRegisterApi: function (gridApi) {
                gridApi.grid.appScope.setGridExtarnals(gridApi)
            },
            paginationPageSizes: [1, 10, 25, 50, 75, 100, 1000],
            paginationPageSize: 50,
            enableColumnMenu: false,
            enableFiltering: true,
            enableCellEdit: false,
            useExternalPagination: true,
            useExternalSorting: true,
            useExternalFiltering: true,
            enableColumnMenus: false,
            showTreeExpandNoChildren: false,
            groupingShowGroupingMenus: false,
            groupingShowAggregationMenus: false,
            columnDefs: []
        },
    });
});

