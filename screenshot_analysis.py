import numpy as np
from PIL import Image
from queue import Queue


def get_pixel_array(image_path):
    image = Image.open(image_path)
    rgb_image = image.convert("RGB")
    width, height = image.size
    pixel_list = [
        [rgb_image.getpixel((i, j)) for j in range(height)] for i in range(width)
    ]
    return np.asarray(pixel_list)


def save_pixel_array(pixel_array, output_path):
    pixel_array = np.swapaxes(pixel_array, axis1=0, axis2=1)
    image = Image.fromarray(np.uint8(pixel_array))
    image.save(output_path)


def get_tube(pixel_array, water_block_per_tube=4):
    has_coded_color_list = []
    def _get_color_code(rgb_array):
        for idx, has_coded_rgb_array in enumerate(has_coded_color_list):
            if np.sum(np.abs(rgb_array - has_coded_rgb_array)) < 10:
                return idx
        has_coded_color_list.append(rgb_array)
        return len(has_coded_color_list) - 1

    width, height, _ = np.shape(pixel_array)
    grey_option_pixels = np.where(np.abs(pixel_array - 187) < 40, 1, 0)
    grey_option_pixels = np.sum(grey_option_pixels, axis=2)
    grey_pixel_tuple = np.where(grey_option_pixels >= 3)
    black_option_pixels = np.where(np.abs(pixel_array - 26) < 30, 1, 0)
    black_option_pixels = np.sum(black_option_pixels, axis=2)
    black_pixel_tuple = np.where(black_option_pixels >= 3)
    connect_map = np.zeros([width, height])
    connect_map[grey_pixel_tuple] = 1
    connect_map[black_pixel_tuple] = 2
    # 有一定的粗度才能被算作试管璧或者背景 检查一下每个被判定为灰色或黑色的像素 它上方的几个像素是不是全部都也是黑色或者灰色
    double_check_x_list = []
    double_check_y_list = []
    for check_x in range(width):
        for check_y in range(height):
            if connect_map[check_x, check_y] != 0:
                check_up = True
                for bias in range(3):
                    if check_y - bias > 0 and connect_map[check_x, check_y - bias] != connect_map[check_x, check_y]:
                        check_up = False
                if check_up == False:
                    double_check_x_list.append(check_x)
                    double_check_y_list.append(check_y)
    connect_map[(np.asarray(double_check_x_list), np.asarray(double_check_y_list))] = 0
    x_array, y_array = grey_pixel_tuple
    connect_grey_pixel_lists = []
    has_judged_pixels = set()
    for seed_x, seed_y in zip(x_array, y_array):
        if (seed_x, seed_y) not in has_judged_pixels:
            queue = Queue()
            connect_grey_pixel_lists.append(([seed_x], [seed_y]))
            has_judged_pixels.add((seed_x, seed_y))
            queue.put((seed_x, seed_y))
            while not queue.empty():
                sub_seed_x, sub_seed_y = queue.get()
                for x in range(sub_seed_x-1, sub_seed_x+2):
                    for y in range(sub_seed_y-1, sub_seed_y+2):
                        if x > 0 and y > 0 and x < width and y < height:
                            if (x, y) not in has_judged_pixels and connect_map[x, y] == 1:
                                block_x_list, block_y_list = connect_grey_pixel_lists[-1]
                                block_x_list.append(x)
                                block_y_list.append(y)
                                has_judged_pixels.add((x, y))
                                queue.put((x, y))
    # 用连通块的像素数和高度的和作为判定连通块规模的依据 试管的连通块 规模相近而且是规模最大的一批
    connect_grey_pixel_lists.sort(key=lambda t: -(len(t[0]) + max(t[1]) - min(t[1])))
    for idx, block in enumerate(connect_grey_pixel_lists):
        if idx == len(connect_grey_pixel_lists) - 1:
            tube_grey_pixel_lists = connect_grey_pixel_lists
        else:
            block_scale = len(block[0]) + max(block[1]) - min(block[1])
            next_block = connect_grey_pixel_lists[idx + 1]
            next_block_scale = len(next_block[0]) + max(next_block[1]) - min(next_block[1])
            if block_scale * 0.8 > next_block_scale:
                tube_grey_pixel_lists = connect_grey_pixel_lists[: idx + 1]
                break
    tube_grey_pixel_tuples = [(np.asarray(t[0]), np.asarray(t[1])) for t in tube_grey_pixel_lists]
    # 整除10 减少误差 先在x轴排序 再在y轴排序
    tube_grey_pixel_tuples.sort(key=lambda t: (min(t[1]) // 10, min(t[0]) // 10))
    tube_stack_list = []
    for tube_grey_pixel_tuple in tube_grey_pixel_tuples:
        tube_stack = []
        middle_x = (max(tube_grey_pixel_tuple[0]) + min(tube_grey_pixel_tuple[0])) // 2
        colorful_pixel_block_count = None
        max_colorful_pixel_block_count = 0
        colorful_pixel_end_y = None
        # 找到中线上最长的彩色像素联通线 平均分成water_block_per_tube份 在中线上给每份的中点采样
        for tube_y in range(min(tube_grey_pixel_tuple[1]), max(tube_grey_pixel_tuple[1])):
            c_u = connect_map[middle_x, tube_y - 1]
            c = connect_map[middle_x, tube_y]
            c_d = connect_map[middle_x, tube_y + 1]
            if c == 0:
                if c_u != c:
                    colorful_pixel_block_count = 1
                elif colorful_pixel_block_count is not None:
                    if c_d != c:
                        if colorful_pixel_block_count > max_colorful_pixel_block_count:
                            max_colorful_pixel_block_count = colorful_pixel_block_count
                            colorful_pixel_end_y = tube_y
                        colorful_pixel_block_count = None
                    else:
                        colorful_pixel_block_count += 1
        # 找到彩色像素才采样 否则是空试管
        if max_colorful_pixel_block_count is not None and max_colorful_pixel_block_count > 10:
            # print(max_colorful_pixel_block_count)
            for idx in range(water_block_per_tube):
                # 自底向上采样
                sample_y = colorful_pixel_end_y - max_colorful_pixel_block_count // (2 * water_block_per_tube) * (2 * idx + 1)
                tube_stack.append(_get_color_code(pixel_array[middle_x, sample_y]))
        tube_stack_list.append(tube_stack)
    
    # save_pixel_array(get_red_mark_pixel_array(np.where(connect_map == 1), (width, height)), "grey.png")
    # save_pixel_array(get_red_mark_pixel_array(np.where(connect_map == 2), (width, height)), "black.png")
    return tube_stack_list, tube_grey_pixel_tuples


def get_red_mark_pixel_array(marked_pixel_tuple, size):
    width, height = size
    x_array, y_array = marked_pixel_tuple
    z_1_array = np.ones(np.shape(marked_pixel_tuple[0]), dtype=np.int64)
    z_2_array = z_1_array * 2
    pixel_array = np.ones([width, height, 3]) * 255
    pixel_array[(x_array, y_array, z_1_array)] = 0
    pixel_array[(x_array, y_array, z_2_array)] = 0
    return pixel_array

