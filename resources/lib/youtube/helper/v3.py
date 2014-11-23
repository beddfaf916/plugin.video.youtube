__author__ = 'bromix'

from resources.lib import kodion
from resources.lib.kodion import items
from . import utils


def _process_list_response(provider, context, json_data):
    video_id_dict = {}
    channel_item_dict = {}
    playlist_item_id_dict = {}

    result = []

    yt_items = json_data.get('items', [])
    if len(yt_items) == 0:
        context.log_warning('List of search result is empty')
        return result

    for yt_item in yt_items:
        yt_kind = yt_item.get('kind', '')
        if yt_kind == u'youtube#subscription':
            snippet = yt_item['snippet']
            image = snippet.get('thumbnails', {}).get('high', {}).get('url', '')
            channel_id = snippet['resourceId']['channelId']
            subscription_item = items.DirectoryItem(snippet['title'],
                                                    context.create_uri(['channel', channel_id]),
                                                    image=image)
            subscription_item.set_fanart(provider.get_fanart(context))

            subscription_id = yt_item['id']
            context_unsubscribe = (context.localize(provider.LOCAL_MAP['youtube.unsubscribe']),
                                   'RunPlugin(%s)' % context.create_uri(['subscription', 'remove', subscription_id]))
            subscription_item.set_context_menu([context_unsubscribe])
            result.append(subscription_item)

            if not channel_id in channel_item_dict:
                channel_item_dict[channel_id] = []
            channel_item_dict[channel_id].append(subscription_item)
            pass
        elif yt_kind == u'youtube#playlist':
            playlist_id = yt_item['id']
            snippet = yt_item['snippet']
            title = snippet['title']
            image = snippet.get('thumbnails', {}).get('medium', {}).get('url', '')

            channel_id = snippet['channelId']
            # we correct the channel id here so we know where we are
            if context.get_path() == '/channel/mine/playlists/':
                channel_id = 'mine'
                pass
            subscription_item = items.DirectoryItem(title,
                                                    context.create_uri(
                                                        ['channel', channel_id, 'playlist', playlist_id]),
                                                    image=image)
            subscription_item.set_fanart(provider.get_fanart(context))
            result.append(subscription_item)
            if not channel_id in channel_item_dict:
                channel_item_dict[channel_id] = []
            channel_item_dict[channel_id].append(subscription_item)
            pass
        elif yt_kind == u'youtube#playlistItem':
            snippet = yt_item['snippet']
            video_id = snippet['resourceId']['videoId']

            # store the id of the playlistItem - for deleting this item we need this item
            playlist_item_id_dict[video_id] = yt_item['id']

            title = snippet['title']
            image = snippet.get('thumbnails', {}).get('medium', {}).get('url', '')
            video_item = items.VideoItem(title,
                                         context.create_uri(['play', video_id]),
                                         image=image)
            video_item.set_fanart(provider.get_fanart(context))
            result.append(video_item)
            video_id_dict[video_id] = video_item

            channel_id = snippet['channelId']
            if not channel_id in channel_item_dict:
                channel_item_dict[channel_id] = []
            channel_item_dict[channel_id].append(video_item)
            pass
        elif yt_kind == 'youtube#searchResult':
            yt_kind = yt_item.get('id', {}).get('kind', '')

            # video
            if yt_kind == 'youtube#video':
                video_id = yt_item['id']['videoId']
                snippet = yt_item['snippet']
                title = snippet['title']
                image = snippet.get('thumbnails', {}).get('medium', {}).get('url', '')
                video_item = items.VideoItem(title,
                                             context.create_uri(['play', video_id]),
                                             image=image)
                video_item.set_fanart(provider.get_fanart(context))
                result.append(video_item)
                video_id_dict[video_id] = video_item

                channel_id = snippet['channelId']
                if not channel_id in channel_item_dict:
                    channel_item_dict[channel_id] = []
                channel_item_dict[channel_id].append(video_item)
                pass
            # playlist
            elif yt_kind == 'youtube#playlist':
                playlist_id = yt_item['id']['playlistId']
                snippet = yt_item['snippet']
                title = snippet['title']
                image = snippet.get('thumbnails', {}).get('medium', {}).get('url', '')

                channel_id = snippet['channelId']
                subscription_item = items.DirectoryItem('[PL]' + title,
                                                        context.create_uri(
                                                            ['channel', channel_id, 'playlist', playlist_id]),
                                                        image=image)
                subscription_item.set_fanart(provider.get_fanart(context))
                result.append(subscription_item)
                if not channel_id in channel_item_dict:
                    channel_item_dict[channel_id] = []
                channel_item_dict[channel_id].append(subscription_item)
                pass
            elif yt_kind == 'youtube#channel':
                channel_id = yt_item['id']['channelId']
                snippet = yt_item['snippet']
                title = snippet['title']
                image = snippet.get('thumbnails', {}).get('medium', {}).get('url', '')

                channel_item = items.DirectoryItem(title,
                                                   context.create_uri(['channel', channel_id]),
                                                   image=image)
                channel_item.set_fanart(provider.get_fanart(context))

                context_subscribe = (context.localize(provider.LOCAL_MAP['youtube.subscribe']),
                                     'RunPlugin(%s)' % context.create_uri(['subscription', 'add', channel_id]))
                channel_item.set_context_menu([context_subscribe])
                result.append(channel_item)

                if not channel_id in channel_item_dict:
                    channel_item_dict[channel_id] = []
                channel_item_dict[channel_id].append(channel_item)
                pass
            else:
                raise kodion.KodimonException("Unknown kind '%s'" % yt_kind)
            pass
        else:
            raise kodion.KodimonException("Unknown kind '%s'" % yt_kind)
        pass

    utils.update_video_infos(provider, context, video_id_dict, playlist_item_id_dict)
    utils.update_channel_infos(provider, context, channel_item_dict)
    return result


def response_to_items(provider, context, json_data):
    result = []

    kind = json_data.get('kind', '')
    if kind == u'youtube#searchListResponse' or kind == u'youtube#playlistItemListResponse' or \
                    kind == u'youtube#playlistListResponse' or kind == u'youtube#subscriptionListResponse':
        result.extend(_process_list_response(provider, context, json_data))
        pass
    else:
        raise kodion.KodimonException("Unknown kind '%s'" % kind)

    # next page
    yt_next_page_token = json_data.get('nextPageToken', '')
    if yt_next_page_token:
        new_params = {}
        new_params.update(context.get_params())
        new_params['page_token'] = yt_next_page_token

        new_context = context.clone(new_params=new_params)

        current_page = int(new_context.get_param('page', 1))
        next_page_item = items.create_next_page_item(new_context, current_page)
        next_page_item.set_fanart(provider.get_fanart(new_context))
        result.append(next_page_item)
        pass

    return result