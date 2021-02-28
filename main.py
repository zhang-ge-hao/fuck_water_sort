from queue import Queue
from screenshot_analysis import get_pixel_array, get_tube


class Tube(object):
    def __init__(self, water_list, capacity):
        self.water_list = water_list
        self.capacity = capacity
        self.size = len(self.water_list)
        assert self.size <= self.capacity
        self.water_list = self.water_list + [None] * (self.capacity - self.size)
    
    def __str__(self):
        return "Tube%s" % str(self.water_list[:self.size])
    
    def is_empty(self):
        return self.size <= 0
    
    def is_full(self):
        return self.size >= self.capacity
    
    def is_pure(self):
        if self.size <= 0:
            return True
        for idx in range(1, self.size):
            if self.water_list[idx] != self.water_list[0]:
                return False
        return True
    
    def get(self):
        assert self.size > 0
        self.size -= 1
        return self.water_list[self.size]
    
    def add(self, code):
        assert self.size < self.capacity
        self.water_list[self.size] = code
        self.size += 1
    
    def top(self):
        return self.water_list[self.size - 1]
    
    def copy(self):
        new_list = [i for i in self.water_list[:self.size]]
        return Tube(new_list, self.capacity)
    
    @classmethod
    def can_dump(cls, from_tube, to_tube):
        if from_tube.is_empty():
            return False
        if to_tube.is_empty():
            return True
        return not to_tube.is_full() and from_tube.top() == to_tube.top()
    
    @classmethod
    def dump(cls, from_tube, to_tube):
        if not Tube.can_dump(from_tube, to_tube):
            return None, None
        new_from_tube = from_tube.copy()
        new_to_tube = to_tube.copy()
        while Tube.can_dump(new_from_tube, new_to_tube):
            new_to_tube.add(new_from_tube.get())
        return new_from_tube, new_to_tube


class State(object):
    def __init__(self, tube_list, log=""):
        self.tube_list = tube_list
        self.log = log
    
    def __str__(self):
        tube_str_list = [str(tube) for tube in self.tube_list]
        tube_str_list.sort()
        return " ".join(tube_str_list)
    
    def is_win(self):
        for tube in self.tube_list:
            if not ((tube.is_full() or tube.is_empty()) and tube.is_pure()):
                return False
        return True

    def next_states(self):
        states = []
        for from_tube_idx in range(len(self.tube_list)):
            for to_tube_idx in range(len(self.tube_list)):
                if from_tube_idx != to_tube_idx:
                    from_tube = self.tube_list[from_tube_idx]
                    to_tube = self.tube_list[to_tube_idx]
                    new_from_tube, new_to_tube = Tube.dump(from_tube, to_tube)
                    if new_from_tube is not None and new_to_tube is not None:
                        new_tube_list = []
                        for idx, ori_tube in enumerate(self.tube_list):
                            if idx == from_tube_idx:
                                new_tube_list.append(new_from_tube)
                            elif idx == to_tube_idx:
                                new_tube_list.append(new_to_tube)
                            else:
                                new_tube_list.append(ori_tube)
                        states.append(State(new_tube_list, "%s%3d -> %3d\n" % (self.log, from_tube_idx + 1, to_tube_idx + 1)))

        return states


if __name__ == '__main__':
    water_block_per_tube = 4
    screenshot_path = "screenshot_4.jpg"
    tube_stack_list, _ = get_tube(get_pixel_array(screenshot_path), water_block_per_tube)
    print(tube_stack_list)
    init_state = State([Tube(li, water_block_per_tube) for li in tube_stack_list])
    has_in_queue_states = set()
    queue = Queue()
    queue.put(init_state)
    has_in_queue_states.add(str(init_state))
    while not queue.empty():
        top_state = queue.get()
        if top_state.is_win():
            print(top_state.log)
            break
        next_states = top_state.next_states()
        for next_state in next_states:
            if str(next_state) not in has_in_queue_states:
                queue.put(next_state)
                has_in_queue_states.add(str(next_state))