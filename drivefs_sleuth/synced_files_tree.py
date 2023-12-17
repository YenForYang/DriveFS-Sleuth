import re
import datetime


class Item:
    def __init__(self, stable_id, url_id, local_title, mime_type, is_owner, file_size, modified_date, viewed_by_me_date,
                 trashed, properties, tree_path):
        self.__stable_id = stable_id
        self.url_id = url_id
        self.local_title = local_title
        self.mime_type = mime_type
        self.is_owner = is_owner
        self.file_size = file_size
        self.modified_date = modified_date
        self.viewed_by_me_date = viewed_by_me_date
        self.trashed = trashed
        self.properties = properties
        self.tree_path = tree_path

    def get_stable_id(self):
        return self.__stable_id

    def is_dir(self):
        return isinstance(self, Directory)

    def is_link(self):
        return isinstance(self, Link)

    def get_modified_date_utc(self):
        return datetime.datetime.fromtimestamp(int(self.modified_date)/1000.0, datetime.timezone.utc)

    def get_viewed_by_me_date_utc(self):
        return datetime.datetime.fromtimestamp(int(self.viewed_by_me_date)/1000.0, datetime.timezone.utc)

    def get_file_size_mb(self):
        return round(int(self.file_size) / 1e+6, 2)

    def to_dict(self):
        item_dict = {
            'stable_id': self.get_stable_id(),
            'url_id': self.url_id,
            'local_title': self.local_title,
            'mime_type': self.mime_type,
            'is_owner': self.is_owner,
            'file_size': self.file_size,
            'modified_date': self.get_modified_date_utc(),
            'viewed_by_me_date': self.get_viewed_by_me_date_utc(),
            'trashed': self.trashed,
            'tree_path': self.tree_path
        }
        for prop_name, prop_value in self.properties.items():
            item_dict[prop_name] = prop_value

        return item_dict


class File(Item):
    def __init__(self, stable_id, url_id, local_title, mime_type, is_owner, file_size, modified_date, viewed_by_me_date,
                 trashed, properties, tree_path):
        super().__init__(stable_id, url_id, local_title, mime_type, is_owner, file_size, modified_date,
                         viewed_by_me_date, trashed, properties, tree_path)


class Directory(Item):
    def __init__(self, stable_id, url_id, local_title, mime_type, is_owner, file_size, modified_date, viewed_by_me_date,
                 trashed, properties, tree_path):
        super().__init__(stable_id, url_id, local_title, mime_type, is_owner, file_size, modified_date,
                         viewed_by_me_date, trashed, properties, tree_path)
        self.__sub_items = []

    def add_item(self, item):
        self.__sub_items.append(item)

    def remove_item(self, stable_id):
        for item in self.__sub_items:
            if item.get_stable_id() == stable_id:
                self.__sub_items.remove(item)

    def get_sub_items(self):
        return self.__sub_items


class Link(Item):
    def __init__(self, stable_id, url_id, local_title, mime_type, is_owner, file_size, modified_date, viewed_by_me_date,
                 trashed, properties, tree_path, target_item):
        super().__init__(stable_id, url_id, local_title, mime_type, is_owner, file_size, modified_date,
                         viewed_by_me_date, trashed, properties, tree_path)
        self.__target_item = target_item

    def get_target_item(self):
        return self.__target_item


class MirrorItem:
    def __init__(self, local_stable_id, stable_id, volume, parent, local_filename, cloud_filename, local_mtime,
                 cloud_mtime, local_md5, cloud_md5, local_size, cloud_size, local_version, cloud_version, shared,
                 read_only, is_root):
        self.local_stable_id = local_stable_id
        self.stable_id = stable_id
        self.volume = volume
        self.parent = parent
        self.local_filename = local_filename
        self.cloud_filename = cloud_filename
        self.local_mtime = local_mtime
        self.cloud_mtime = cloud_mtime
        self.local_md5 = local_md5
        self.cloud_md5 = cloud_md5
        self.local_size = local_size
        self.cloud_size = cloud_size
        self.local_version = local_version
        self.cloud_version = cloud_version
        self.shared = shared
        self.read_only = read_only
        self.is_root = is_root

    def get_local_mtime_utc(self):
        return datetime.datetime.fromtimestamp(int(self.local_mtime)/1000.0, datetime.timezone.utc)

    def get_cloud_mtime_utc(self):
        return datetime.datetime.fromtimestamp(int(self.cloud_mtime)/1000.0, datetime.timezone.utc)


def _print_tree(roots, indent=''):
    if isinstance(roots, File):
        print(f'{indent}- ({roots.get_stable_id()}) {roots.local_title} - ({roots.tree_path})')

    elif isinstance(roots, Link):
        print(f'{indent}+ ({roots.get_stable_id()}) {roots.local_title} - ({roots.tree_path})')

        for sub_item in roots.get_target_item().get_sub_items():
            _print_tree(sub_item, indent + f'\t')

    elif isinstance(roots, Directory):
        print(f'{indent}+ ({roots.get_stable_id()}) {roots.local_title} - ({roots.tree_path})')

        for sub_item in roots.get_sub_items():
            _print_tree(sub_item, indent + f'\t')

    else:
        for item in roots:
            _print_tree(item, indent)


class SyncedFilesTree:
    def __init__(self, root):
        self.__root = root
        self.__orphan_items = []
        self.__shared_with_me = []
        self.__deleted_items = []
        self.__mirror_items = []

    def get_root(self):
        return self.__root

    def get_orphan_items(self):
        return self.__orphan_items

    def add_orphan_item(self, item):
        self.__orphan_items.append(item)

    def add_deleted_item(self, stable_id):
        self.__deleted_items.append(stable_id)

    def add_shared_with_me_item(self, item):
        self.__shared_with_me.append(item)

    def get_shared_with_me_items(self):
        return self.__shared_with_me

    def get_deleted_items(self):
        return self.__deleted_items

    def get_item_by_id(self, target_id, orphan=False):
        if not orphan:
            dirs_queue = [self.get_root()] + self.get_orphan_items()
        else:
            dirs_queue = self.get_orphan_items()

        while dirs_queue:
            current_dir = dirs_queue.pop(0)

            for item in current_dir.get_sub_items():
                if item.get_stable_id() == target_id:
                    return item

                else:
                    if item.is_dir():
                        dirs_queue.append(item)

        return None

    def search_item_by_name(self, filenames=None, regex=None, contains=True, list_sub_items=True):
        if filenames is None:
            filenames = []
        if regex is None:
            regex = []
        items = []

        def append_item_childs(item):
            items.append(item)
            if isinstance(item, File):
                return

            elif isinstance(item, Link):
                for sub_item in item.get_target_item().get_sub_items():
                    append_item_childs(sub_item)

            elif isinstance(item, Directory):
                for sub_item in item.get_sub_items():
                    append_item_childs(sub_item)

            else:
                for sub_item in item:
                    append_item_childs(sub_item)

        def search(current_item):
            hit = False
            if regex:
                for exp in regex:
                    match = re.search(exp, current_item.local_title)
                    if match:
                        items.append(current_item)
                        hit = True

            if contains:
                for filename in filenames:
                    if filename.lower() in current_item.local_title.lower():
                        items.append(current_item)
                        hit = True
            else:
                for filename in filenames:
                    if filename.lower() == current_item.local_title.lower():
                        items.append(current_item)
                        hit = True

            if isinstance(current_item, File):
                return

            elif isinstance(current_item, Link) and hit and list_sub_items:
                for sub_item in current_item.get_target_item().get_sub_items():
                    append_item_childs(sub_item)

            elif isinstance(current_item, Directory) and hit and list_sub_items:
                for sub_item in current_item.get_sub_items():
                    append_item_childs(sub_item)

            else:
                if isinstance(current_item, Link):
                    for sub_item in current_item.get_target_item().get_sub_items():
                        search(sub_item)
                else:
                    for sub_item in current_item.get_sub_items():
                        search(sub_item)

        search(self.get_root())
        for orphan_item in self.get_orphan_items():
            search(orphan_item)

        for shared_item in self.get_shared_with_me_items():
            search(shared_item)

        return items

    def add_mirrored_item(self, mirrored_item):
        self.__mirror_items.append(mirrored_item)

    def get_mirrored_items(self):
        return self.__mirror_items

    def print_synced_files_tree(self):
        print('\n----------Synced Items----------\n')

        _print_tree([self.get_root()] + self.get_orphan_items())

        print('\n----------Deleted Items----------\n')

        for deleted_item in self.__deleted_items:
            print(f'- {deleted_item}')

        print('\n----------Orphan Items----------\n')

        for orphan in self.get_orphan_items():
            print(f'- ({orphan.get_stable_id()}) {orphan.local_title}')

        print('\n----------Shared With Me Items----------\n')

        for shared_with_me_item in self.get_shared_with_me_items():
            print(f'- ({shared_with_me_item.get_stable_id()}) {shared_with_me_item.local_title}')
