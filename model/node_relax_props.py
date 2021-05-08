import bpy


class NodeRelaxProps(bpy.types.PropertyGroup):
    #### Brush settings

    IsRunning: bpy.props.BoolProperty(default=False)
    BrushSize: bpy.props.FloatProperty(default=150)
    Distance: bpy.props.FloatProperty(
        name="Distance",
        description="Target distance between nodes",
        default=80)
    RelaxPower: bpy.props.FloatProperty(
        name="Relax power",
        min=0,
        soft_max=0.2,
        max=1,
        default=0.1)
    SlidePower: bpy.props.FloatProperty(
        name="Slide power",
        min=0,
        max=1,
        default=0.6)
    CollisionPower: bpy.props.FloatProperty(
        name="Collision power",
        min=0,
        max=1,
        default=0.9)

    #### Arrange settings

    ArrangeOnlySelected: bpy.props.BoolProperty(
        name="Only Selected",
        default=False)
    Iterations_S1: bpy.props.IntProperty(
        name="Step 1",
        min=0,
        default=200)
    Iterations_S2: bpy.props.IntProperty(
        name="Step 2",
        min=0,
        default=200)
    Iterations_S3: bpy.props.IntProperty(
        name="Step 3",
        min=0,
        default=200)
    Iterations_S4: bpy.props.IntProperty(
        name="Step 4",
        min=0,
        default=200)
    AdaptiveIters: bpy.props.BoolProperty(
        name="Adaptive Iterations",
        default=True)
    BackgroundIterations: bpy.props.IntProperty(
        name="Background Iterations",
        min=0,
        max=10,
        default=2)
    ArrangeState: bpy.props.StringProperty(default="")
