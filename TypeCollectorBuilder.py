
import cmp.visitor as visitor

from AST import ProgramNode, ClassDeclarationNode, FuncDeclarationNode, AttrDeclarationNode
from cmp.semantic import SemanticError
from cmp.semantic import Attribute, Method, Type
from cmp.semantic import VoidType, ErrorType, SelfType
from cmp.semantic import Context

class TypeCollector(object):
    def __init__(self, errors=[]):
        self.context = None
        self.errors = errors
        
        self.class_tree = dict()
        self.class_tree["Object"] = ["IO", "String", "Int", "Bool"]
        self.types_nodes = dict()
    
    @visitor.on('node')
    def visit(self, node):
        pass
    
    @visitor.when(ProgramNode)
    def visit(self, node):
        self.context = Context()
        self.init_default_classes()
        
        for class_def in node.declarations:
            self.visit(class_def)
        
        ordered = []
        self.check_type_tree(ordered, self.class_tree)
        node.declarations = ordered
    
    @visitor.when(ClassDeclarationNode)
    def visit(self, node):
        try:
            self.context.create_type(node.id)
            #Check Class Name starts with upper case
            self.types_nodes[node.id] = node
            if node.parent:
                try:
                    self.class_tree[node.parent].append(node.id)
                except KeyError:
                    self.class_tree[node.parent] = [node.id]
            else:
                node.parent = "Object"
                self.class_tree["Object"].append(node.id)
                
        except SemanticError as err:
            self.errors.append(err.text)

    def init_default_classes(self):
        self.context.create_type('Object').index = 0
        self.context.create_type('String')
        self.context.create_type('Int')
        self.context.create_type('IO')
        self.context.create_type('Bool')

    def check_type_tree(self, ordered, graph):
        visited = set(["Object"])
        dfsSimple("Object", graph, visited, self.context, self.types_nodes, ordered, 1)

        for node in graph:
            if not node in visited:
                visited.add(node)
                self.errors.append("Circular Heritage: " + dfsError(node, graph, [node], visited))

def dfsSimple(root, graph, visited : set, context, types, ordered, index):
    try:
        for node in graph[root]:
            if not node in visited:
                visited.add(node)
                if node not in {"Int", "String", "IO", "Bool", "Object"}:
                    ordered.append(types[node])
                context.get_type(node).index = index
                dfsSimple(node, graph, visited, context, types, ordered, index + 1)
    except KeyError:
        pass

def dfsError(root, graph, visited : list, set_visited : set):
        try:
            for node in graph[root]:
                if node in visited:
                    return show_circular_heritage(visited, node)

                set_visited.add(node)
                visited.append(node)
                err = dfsError(node, graph, visited, set_visited)
                if err:
                    return err
                visited.pop()
        except KeyError:
            return ""

def show_circular_heritage(visited : list, node):
    visited.append(f"[{node}]")
    visited[0] = visited[-1] 
    s = " -> ".join(child for child in visited)
    return s

class TypeBuilder:
    def __init__(self, context, errors=[]):
        self.context = context
        self.current_type = None
        self.errors = errors
    
    @visitor.on('node')
    def visit(self, node):
        pass
    
    @visitor.when(ProgramNode)
    def visit(self, node):
        self.build_default_classes()

        for class_def in node.declarations:
            self.visit(class_def)

        try:
            self.context.get_type('Main').get_method('main')
        except SemanticError as err:
            self.errors.append(err.text)
    
    @visitor.when(ClassDeclarationNode)
    def visit(self, node):
        self.current_type = self.context.get_type(node.id)
        
        if node.parent:
            try:
                parent_type = self.context.get_type(node.parent)
                self.current_type.set_parent(parent_type)
                for idx, _ in list(parent_type.all_attributes(True)):
                    self.current_type.attributes.append(idx)
            except SemanticError as err:
                self.errors.append(err.text)
        
        for feature in node.features:
            self.visit(feature)
    
    @visitor.when(AttrDeclarationNode)
    def visit(self, node):
        try:
            attr_type = self.context.get_type(node.type) if node.type != "SELF_TYPE" else SelfType()
        except SemanticError as err:
            self.errors.append(err.text)
            attr_type = ErrorType()
            
        try:
            self.current_type.define_attribute(node.id, attr_type)
        except SemanticError as err:
            self.errors.append(err.text)
    
    @visitor.when(FuncDeclarationNode)
    def visit(self, node):
        try:
            ret_type = self.context.get_type(node.type) if node.type != 'SELF_TYPE' else SelfType()
        except SemanticError as err:
            self.errors.append(err.text)
            ret_type = ErrorType()
            
        params_type = []
        params_name = []
        for p_name, p_type in node.params:
            try:
                params_type.append(self.context.get_type(p_type))
            except SemanticError as err:
                params_type.append(ErrorType())
                self.errors.append(err.text)
            params_name.append(p_name)
            
        try:
            self.current_type.define_method(node.id, params_name, params_type, ret_type)
        except SemanticError as err:
            self.errors.append(err.text)
    
    def build_default_classes(self):
        Object = self.context.get_type("Object")
        String = self.context.get_type("String")
        Int = self.context.get_type("Int")
        IO = self.context.get_type("IO")
        Bool = self.context.get_type("Bool")

        String.set_parent(Object)
        Int.set_parent(Object)
        IO.set_parent(Object)
        Bool.set_parent(Object)

        Object.define_method("abort", [], [], Object)
        Object.define_method("type_name", [], [], String)
        Object.define_method("copy", [], [], SelfType())

        String.define_method("length", [], [], Int)
        String.define_method("concat", ["s"], [String], String)
        String.define_method("substr", ["i", "l"], [Int, Int], String)

        IO.define_method("out_string", ["x"],[String], SelfType())
        IO.define_method("out_int", ["x"],[Int],SelfType())
        IO.define_method("in_string", [],[], String)
        IO.define_method("in_int", [], [], Int)

