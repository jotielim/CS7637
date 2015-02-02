# Your Agent for solving Raven's Progressive Matrices. You MUST modify this file.
#
# You may also create and submit new files in addition to modifying this file.
#
# Make sure your file retains methods with the signatures:
# def __init__(self)
# def Solve(self,problem)
#
# These methods will be necessary for the project's main method to run.
from itertools import permutations, combinations
import copy

class Agent:
    # The default constructor for your Agent. Make sure to execute any
    # processing necessary before your Agent starts solving problems here.
    #
    # Do not add any variables to this signature; they will not be used by
    # main().
    def __init__(self):
        pass

    # The primary method for solving incoming Raven's Progressive Matrices.
    # For each problem, your Agent's Solve() method will be called. At the
    # conclusion of Solve(), your Agent should return a String representing its
    # answer to the question: "1", "2", "3", "4", "5", or "6". These Strings
    # are also the Names of the individual RavensFigures, obtained through
    # RavensFigure.getName().
    #
    # In addition to returning your answer at the end of the method, your Agent
    # may also call problem.checkAnswer(String givenAnswer). The parameter
    # passed to checkAnswer should be your Agent's current guess for the
    # problem; checkAnswer will return the correct answer to the problem. This
    # allows your Agent to check its answer. Note, however, that after your
    # agent has called checkAnswer, it will#not* be able to change its answer.
    # checkAnswer is used to allow your Agent to learn from its incorrect
    # answers; however, your Agent cannot change the answer to a question it
    # has already answered.
    #
    # If your Agent calls checkAnswer during execution of Solve, the answer it
    # returns will be ignored; otherwise, the answer returned at the end of
    # Solve will be taken as your Agent's answer to this problem.
    #
    # @param problem the RavensProblem your agent should solve
    # @return your Agent's answer to this problem
    def Solve(self, problem):
        guess = ''

        # convert problem to python dictionary
        problem_dict = Util.convert_problem_to_dict(problem)
        figures = problem_dict.get('figures')

        if problem_dict.get('type') == '2x1':
            guess = self.solve2x1(figures)

        return guess

    def solve2x1(self, figures):
        """
        Method for solving 2x1 RPM

        :param figures:
        :return:
        """
        # Try to identify the objects between figures
        ab_map = self.map_identity(figures.get('A'), figures.get('B'))
        ac_map = self.map_identity(figures.get('A'), figures.get('C'), False)

        # Get the semantic network A to B
        semantic_network_ab = self.get_semantic_network(figures.get('A'), figures.get('B'), ab_map)

        # Using the semantic network A to B, create a guess figure
        guess = self.create_guess_figure(figures, semantic_network_ab, ab_map, ac_map)

        num_diff_ab = len(figures.get('A')) - len(figures.get('B'))
        fig_c_shape = self.get_shape(figures.get('C'))

        matches = []
        options = {}
        options_name = [n for n in figures.keys() if n not in ['A', 'B', 'C']]
        # For each option 1 through 6, match option to the guess figure
        for name in options_name:
            option = figures.get(name)

            # Assume that the difference between A to B and C to D should be the same
            # i.e. if the objects are deleted or added in A to B, then C to D should get the same transformation
            num_diff_cd = len(figures.get('C')) - len(option)
            if num_diff_ab != num_diff_cd:
                continue

            # Check if ab_map.get('matchShape') is True, then C to D should be matched my shape as well
            # If shape is different between C and 1 throught 6, ignore
            if ab_map.get('matchShape'):
                fig_d_shape = self.get_shape(figures.get(name))
                if not set(fig_c_shape) <= set(fig_d_shape) and not set(fig_d_shape) <= set(fig_c_shape):
                    continue

            # Normalize the object name
            cd_map = self.map_identity(figures.get('C'), option, ab_map.get('matchShape'))
            object_name_set = set(option.keys()) | set(figures.get('C'))
            new_guess = self.get_normalized_name_guess(guess, cd_map, object_name_set)

            options[name] = new_guess

            # Find the most similar figures between option and C
            match = self.match_figures_new(option, new_guess, cd_map, ab_map.get('matchShape'))
            match['name'] = name
            matches.append(match)

        matches = sorted(matches, key=lambda x: x.get('weight'), reverse=True)

        match_list = []
        for match in matches:
            if match.get('weight') == matches[0].get('weight'):
                match_list.append(match)
        matches = match_list

        # if unsure and matches length is exactly the number of options and all the options are unique,
        # then we assume this is special polygon case
        edge_map = {
            'triangle': 3,
            'square': 4,
            'pentagon': 5,
            'hexagon': 6,
            'heptagon': 7,
            'octagon': 8
        }

        shape_list = []
        for name in options_name:
            shape_list += self.get_shape(figures.get(name))
        if len(set(shape_list)) == len(set(edge_map.keys())):
            m_list = []

            edge_count_a = self.get_edge_count(figures.get('A'), edge_map)
            edge_count_b = self.get_edge_count(figures.get('B'), edge_map)
            edge_count_c = self.get_edge_count(figures.get('C'), edge_map)

            ratio = edge_count_b / float(edge_count_a)

            for name in options_name:
                edge_count_d = self.get_edge_count(figures.get(name), edge_map)
                if (edge_count_c * ratio) == edge_count_d:
                    m_list.append({'weight': 1, 'name': name})
                    break
            if len(m_list) == 1:
                matches = m_list
        # end of special polygon case

        return matches[0].get('name')

    def get_shape(self, figure):
        """
        Method to get shape from all objects in the figure

        :param figure:
        :return:
        """
        return [shape for name, sublist in figure.iteritems() for shape in sublist.get('shape')]
    
    def get_edge_count(self, figure, edge_map):
        """
        Method to get the edge count

        :param figure:
        :param edge_map:
        :return:
        """
        edge_list = [edge_map.get(shape) for name, obj in figure.iteritems() for shape in obj.get('shape')]
        return sum(edge_list)

    def create_guess_figure(self, figures, semantic_network_ab, ab_map, ac_map):
        """
        Method to create possible solution using the semantic network and name mapping

        :param figures:
        :param semantic_network_ab:
        :param ab_map:
        :param ac_map:
        :return:
        """
        inv_ab_map = dict(zip(ab_map.values(), ab_map.keys()))
        guess = {}
        for src_name, dest_name in ac_map.iteritems():
            if src_name != 'matchShape':
                obj_c = figures.get('C').get(src_name)

                ab = str(src_name) + '->' + str(ab_map.get(src_name))
                ab_transform = semantic_network_ab.get(ab)

                obj_guess = {}
                for attr in ab_transform:
                    if attr != 'position':
                        if ab_transform.get(attr).get('transformation') == 'unchanged':
                            obj_guess[attr] = obj_c.get(attr)
                        elif ab_transform.get(attr).get('transformation') == 'changed':
                            if ab_transform.get(attr).get('from') == obj_c.get(attr):
                                obj_guess[attr] = ab_transform.get(attr).get('to')
                            else:
                                if attr == 'angle':
                                    angle_from = ab_transform.get(attr).get('from')
                                    angle_to = ab_transform.get(attr).get('to')
                                    angle_from = int(angle_from[0]) if angle_from is not None else 0
                                    angle_to = int(angle_to[0]) if angle_to is not None else 0
                                    angle_change = abs(angle_from - angle_to)
                                    obj_c_angle_from = int(obj_c.get(attr)[0]) if obj_c.get(attr) is not None else 0

                                    angle_final = (obj_c_angle_from + angle_change) % 360
                                    obj_guess[attr] = [str(angle_final)]
                                elif attr != 'shape':
                                    val1 = obj_c.get(attr) or []
                                    val2 = ab_transform.get(attr).get('to')
                                    obj_guess[attr] = list(set(val1) | set(val2))
                    elif attr == 'position':
                        for name, pos in ab_transform.get(attr).iteritems():
                            if pos.get('to') is not None:
                                if pos.get('to') in obj_guess:
                                    obj_guess[pos.get('to')].append(inv_ab_map.get(name))
                                else:
                                    obj_guess[pos.get('to')] = [inv_ab_map.get(name)]

                guess[dest_name] = obj_guess

        return guess

    def get_normalized_name_guess(self, guess, cd_map, object_name_set):
        """
        Method to normalize the name in guess figure

        :param guess:
        :param cd_map:
        :param object_name_set:
        :return:
        """
        new_guess = {}
        guess_clone = copy.deepcopy(guess)
        for src_name, dest_name in cd_map.iteritems():
            if src_name != 'matchShape':
                if src_name in guess_clone:
                    new_guess[dest_name] = guess_clone.get(src_name)
                    for attr_name, val in guess_clone.get(src_name).iteritems():
                        if val is not None and set(val) <= object_name_set:
                            new_guess[dest_name][attr_name] = []
                            for rel_name in val:
                                if cd_map.get(rel_name) is None:
                                    new_guess[dest_name][attr_name].append(src_name)
                                else:
                                    new_guess[dest_name][attr_name].append(cd_map.get(rel_name))

        return new_guess

    def match_figures_new(self, option_figure, guess_figure, cd_map, by_shape=False):
        """
        Method to match option figure and guess figure

        :param option_figure:
        :param guess_figure:
        :param cd_map:
        :param by_shape:
        :return:
        """
        object_name_set = set(option_figure.keys()) | set(guess_figure.keys())

        similarity_points = 0

        for name, obj in option_figure.iteritems():
            option_obj = option_figure.get(name)
            guess_obj = guess_figure.get(name)

            if guess_obj is not None:
                similarity_points += self.get_similarity_points(option_obj, guess_obj, object_name_set, by_shape)

        return {'weight': similarity_points}

    def match_figures(self, option_figure, guess_figure, cd_map, by_shape=False):
        """
        Method to match

        """
        object_name_set = set(option_figure.keys()) | set(guess_figure.keys())

        new_option_figure = copy.deepcopy(option_figure)
        extra = []
        if len(option_figure.keys()) < len(object_name_set):
            extra = object_name_set - set(option_figure.keys())
        elif len(guess_figure.keys()) < len(object_name_set):
            extra = object_name_set - set(guess_figure.keys())
        for o in extra:
            new_option_figure[o] = {}

        permute_list = get_possible_permutation(new_option_figure, guess_figure)

        matches_list = []

        for pair_list in permute_list:
            similarity_points = 0
            for pair in pair_list:
                option_obj = new_option_figure.get(pair[0])
                guess_obj = guess_figure.get(pair[1])

                if guess_figure.get(pair[1]) is not None:
                    option_obj_shape = option_obj.get('shape')
                    guess_obj_shape = guess_obj.get('shape')
                    is_shape_equal = False
                    if option_obj_shape is not None and guess_obj_shape is not None:
                        if set(option_obj_shape) == set(guess_obj_shape):
                            is_shape_equal = True
                    # if we are comparing by shape and shape is equal, add extra point
                    if by_shape and is_shape_equal:
                        similarity_points += 1
                    similarity_points += self.get_similarity_points(option_obj, guess_obj, object_name_set)

            matches_list.append({'weight': similarity_points, 'pairList': pair_list})

        matches_list = sorted(matches_list, key=lambda x: x.get('weight'), reverse=True)

        return matches_list[0]

    def get_semantic_network(self, figure1, figure2, relationship_map):
        """
        Method to get the semantic network from two figures

        :param figure1:
        :param figure2:
        :param relationship_map:
        :return:
        """
        object_name_set = set(figure1.keys()) | set(figure2.keys())
        transformation_map = {}

        for src_name, dest_name in relationship_map.iteritems():
            if src_name != 'matchShape':
                transformation_map[str(src_name)+'->'+str(dest_name)] = \
                    self.get_transformation(figure1.get(src_name), figure2.get(dest_name), object_name_set)

        return transformation_map

    def get_transformation(self, src_obj, dest_obj, object_name_set):
        """
        Method to get the transformation between two objects

        :param src_obj:
        :param dest_obj:
        :param object_name_set:
        :return:
        """
        t_map = {}
        if src_obj is not None and dest_obj is not None:
            src_attrs = src_obj.keys()
            dest_attrs = dest_obj.keys()

            pos_map = {}
            for src_attr in src_attrs:
                if src_attr in dest_attrs:
                    dest_attrs.remove(src_attr)
                    if set(src_obj.get(src_attr)) <= object_name_set:
                        self.assign_position(src_attr, src_obj, pos_map, 'from')
                        self.assign_position(src_attr, dest_obj, pos_map, 'to')
                    else:
                        t_map[src_attr] = self.compare_attribute(src_obj.get(src_attr), dest_obj.get(src_attr))
                else:
                    # check if this is position attr such as inside, left-of, above, etc
                    if set(src_obj.get(src_attr)) <= object_name_set:
                        self.assign_position(src_attr, src_obj, pos_map, 'from')
                    else:
                        t_map[src_attr] = self.delete_attribute(src_obj.get(src_attr))
            for dest_attr in dest_attrs:
                if set(dest_obj.get(dest_attr)) <= object_name_set:
                    self.assign_position(dest_attr, dest_obj, pos_map, 'to')
                else:
                    t_map[dest_attr] = self.add_attribute(dest_obj.get(dest_attr))
            if len(pos_map):
                t_map['position'] = pos_map
        # elif src_obj is not None and dest_obj is None:
        #     print '*** deleted ***'

        return t_map

    def compare_attribute(self, src_val, dest_val):
        """
        Method to compare attribute and return dictionary with change/unchanged mapping

        :param src_val:
        :param dest_val:
        :return:
        """
        attr_map = {
            'from': src_val,
            'to': dest_val,
            'transformation': 'unchanged'
        }
        if set(src_val) != set(dest_val):
            attr_map['transformation'] = 'changed'

        return attr_map

    def delete_attribute(self, src_val):
        """
        Method to return dictionary of deleted object

        :param src_val:
        :return:
        """
        return {
            'from': src_val,
            'to': None,
            'transformation': 'deleted'
        }

    def add_attribute(self, dest_val):
        """
        Method to return dictionary of added object

        :param dest_val:
        :return:
        """
        return {
            'from': None,
            'to': dest_val,
            'transformation': 'added'
        }

    def assign_position(self, attr, obj, pos_map, loc):
        """
        Method to assign position when objects are moved

        :param attr:
        :param obj:
        :param pos_map:
        :param loc:
        :return:
        """
        for name in obj.get(attr):
            if name in pos_map:
                pos_map[name][loc] = attr
            else:
                pos_map[name] = {
                    loc: attr
                }
        return pos_map

    def map_identity(self, figure1, figure2, by_shape=True):
        """
        Check relationship between two figures
            1. First, check by shape, continue check by attributes
            2. If shapes do not match, check by attributes
        :param figure1:
        :param figure2:
        :return:
        """

        permute_list = get_possible_permutation(figure1, figure2)

        object_name_set = set(figure1.keys()) | set(figure2.keys())

        # if shapes in f2 is a subset of shapes in f1, do shape similarity
        shapes_figure1 = [shape for name, sublist in figure1.iteritems() for shape in sublist.get('shape')]
        shapes_figure2 = [shape for name, sublist in figure2.iteritems() for shape in sublist.get('shape')]

        match_by_shape = False  # match by shape or attributes
        if set(shapes_figure1) <= set(shapes_figure2) or set(shapes_figure1) >= set(shapes_figure2):
            match_by_shape = True and by_shape

        relationship_map = {
            'matchShape': match_by_shape
        }


        matches_list = []
        for pair_list in permute_list:
            similarity_points = 0
            shape_match_list = []

            for pair in pair_list:
                f1 = figure1.get(pair[0])
                f2 = figure2.get(pair[1])

                # Match by shape, then weight attributes. Reject if shape doesn't match
                if match_by_shape:
                    # Match by shape. Only care about the network from and to the same shape
                    if set(f1.get('shape')) == (f2 and set(f2.get('shape'))):
                        similarity_points += self.get_similarity_points(f1, f2, object_name_set, match_by_shape)
                    else:
                        # if shape is not match, then break
                        break

                    shape_match_list.append(True)
                elif not match_by_shape:
                    if f2 is not None:
                        similarity_points += self.get_similarity_points(f1, f2, object_name_set)

            matches_list.append({'similarityPoints': similarity_points, 'pairList': pair_list})

        matches_list = sorted(matches_list, key=lambda x: x.get('similarityPoints'), reverse=True)
        match = matches_list[0]

        pair_list = match.get('pairList')
        for pair in pair_list:
            relationship_map[pair[0]] = pair[1]

        return relationship_map

    def get_similarity_points(self, f1, f2, object_name_set, by_shape=False):
        """
        Method to calculate the similarity points

        :param f1:
        :param f2:
        :param object_name_set:
        :param by_shape:
        :return similarity_point:
        """
        src_attrs = f1.keys()
        if 'shape' in src_attrs:
            src_attrs.remove('shape')
        dest_attrs = f2.keys()
        if 'shape' in dest_attrs:
            dest_attrs.remove('shape')

        attr_counter = 0

        # if match by shape
        if by_shape and f1.get('shape') is not None and f2.get('shape') is not None:
            if set(f1.get('shape')) == set(f2.get('shape')):
                attr_counter += 1

        # if f2 is empty figure (delete transition), assign less weight
        if len(f2) == 0:
            attr_counter -= 1

        pos_list = []
        pos_map = {}
        for src_attr in src_attrs:
            if src_attr in dest_attrs:
                dest_attrs.remove(src_attr)
                if set(f1.get(src_attr)) == set(f2.get(src_attr)):
                    if set(f1.get(src_attr)) <= object_name_set:
                        # assign higher weight if position unchanged
                        attr_counter += 1
                    attr_counter += 1
                else:
                    if by_shape:
                        attr_counter += 0.5
            else:
                # check if this is position attr such as inside, left-of, above, etc
                if set(f1.get(src_attr)) <= object_name_set:
                    pos_list.append(src_attr)
                    self.assign_position(src_attr, f1, pos_map, 'from')
                else:
                    # if attr(src) not in dest_attrs, and if not position attr, it means we are deleting the attr
                    # reduce similarity point
                    attr_counter -= 1

        for dest_attr in dest_attrs:
            if f2.get(dest_attr) is not None and set(f2.get(dest_attr)) <= object_name_set:
                pos_list.append(dest_attr)
                self.assign_position(dest_attr, f2, pos_map, 'to')
            else:
                # if not position attr, adding new attr
                # reduce similarity point
                attr_counter -= 1

        return attr_counter

def get_possible_permutation(src_figure, dest_figure):
    """
    Given the shapes in two objects, map the possible transformation
    i.e. shapes_a = ['Z', 'Y', 'X'], shapes_b = ['Z', 'Y']
    the possible maps are
    [  # tier
        [  # transformation_list
            [('Y', 'Y'), ('X', 'Z'), ('Z', None)],
            [('Y', 'Y'), ('Z', 'Z'), ('X', None)],
            [('X', 'Y'), ('Y', 'Z'), ('Z', None)],
            [('X', 'Y'), ('Z', 'Z'), ('Y', None)],
            [('Z', 'Y'), ('Y', 'Z'), ('X', None)],
            [('Z', 'Y'), ('X', 'Z'), ('Y', None)]
        ]
    ]

    :param src_figure:
    :param dest_figure:
    :return:
    """

    src_objects = src_figure.keys()
    dest_objects = dest_figure.keys()

    src_lists = permutations(range(len(src_objects)))
    dest_lists = combinations(range(len(dest_objects)), len(dest_objects))

    results = []

    for dest_list in dest_lists:
        for src_list in src_lists:
            inner_list = []
            for index, s in enumerate(src_list):
                inner_list.append((src_objects[s], dest_objects[dest_list[index]] if len(dest_list) > index else None))
            results.append(inner_list)

    return results

class Util:
    def __init__(self):
        pass

    @staticmethod
    def convert_problem_to_dict(problem):
        """
        Method to convert the RPM into python dictionary

        :param problem:
        :return:
        """

        py_problem = {}
        figures = {}
        for name in problem.getFigures():
            items = {}
            figure = problem.getFigures().get(name)
            for object in figure.getObjects():
                attrs = {}
                for attr in object.getAttributes():
                    if ',' in attr.getValue():
                        attrs[attr.getName()] = attr.getValue().split(',')
                    else:
                        attrs[attr.getName()] = [attr.getValue()]
                items[object.getName()] = attrs
            figures[name] = items

        py_problem['figures'] = figures
        py_problem['name'] = problem.getName()
        py_problem['type'] = problem.getProblemType()
        return py_problem