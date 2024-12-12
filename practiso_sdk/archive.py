import xml.etree.ElementTree as Xml
from datetime import datetime, UTC
from typing import Callable, Any

NAMESPACE = 'http://schema.zhufucdev.com/practiso'


def _get_attribute_safe(element: Xml.Element, attr_name: str, convert: Callable[[str], Any] | None = None) -> Any:
    if attr_name not in element.attrib:
        raise TypeError(f'Missing attribute {attr_name} in tag {element.tag}')
    if convert:
        return convert(element.attrib[attr_name])
    else:
        return element.attrib[attr_name]


def _get_simple_tag_name(element: Xml.Element):
    rb = element.tag.index('}')
    if rb < 0:
        return element.tag
    else:
        return element.tag[rb + 1:]


def _namespace_extended(tag: str):
    return '{' + NAMESPACE + '}' + tag


class ArchiveFrame:
    def append_to_element(self, element: Xml.Element):
        pass

    @staticmethod
    def parse_xml_element(element: Xml.Element) -> 'ArchiveFrame':
        tag_name = _get_simple_tag_name(element)
        if tag_name == 'text':
            return Text.parse_xml_element(element)
        elif tag_name == 'image':
            return Image.parse_xml_element(element)
        elif tag_name == 'options':
            return Options.parse_xml_element(element)

    def __hash__(self):
        raise RuntimeError(f'Unimplemented method __hash__ for {type(self).__name__}')


class Text(ArchiveFrame):
    content: str

    def __init__(self, content: str):
        self.content = content

    def append_to_element(self, element: Xml.Element):
        sub = Xml.SubElement(element, 'text')
        sub.text = self.content

    @staticmethod
    def parse_xml_element(element: Xml.Element) -> 'Text':
        if _get_simple_tag_name(element) != 'text':
            raise TypeError(f'Unexpected tag {_get_simple_tag_name(element)}')

        return Text(element.text)

    def __hash__(self):
        return hash(self.content) * 31

    def __eq__(self, other):
        return isinstance(other, Text) and other.content == self.content


class Image(ArchiveFrame):
    filename: str
    width: int
    height: int
    alt_text: str | None

    def __init__(self, filename: str, width: int, height: int, alt_text: str | None = None):
        self.filename = filename
        self.width = width
        self.height = height
        self.alt_text = alt_text

    def append_to_element(self, element: Xml.Element):
        sub = Xml.SubElement(element, 'image',
                             attrib={'src': self.filename, 'width': str(self.width), 'height': str(self.height)})
        if self.alt_text:
            sub.attrib['alt'] = self.alt_text

    @staticmethod
    def parse_xml_element(element: Xml.Element) -> 'Image':
        if _get_simple_tag_name(element) != 'image':
            raise TypeError(f'Unexpected tag {_get_simple_tag_name(element)}')

        return Image(
            filename=_get_attribute_safe(element, 'src'),
            width=_get_attribute_safe(element, 'width', int),
            height=_get_attribute_safe(element, 'height', int),
            alt_text=element.attrib['alt'] if 'alt' in element.attrib else None
        )

    def __hash__(self):
        return hash(self.alt_text) * 31 + hash(self.filename) * 31 + hash(self.width * 31 + self.height) * 31

    def __eq__(self, other):
        return isinstance(other, Image) and other.width == self.width \
            and other.height == self.height \
            and other.filename == self.filename \
            and other.alt_text == self.alt_text


class OptionItem:
    is_key: bool
    priority: int
    content: ArchiveFrame

    def __init__(self, content: ArchiveFrame, is_key: bool = False, priority: int = 0):
        self.content = content
        self.is_key = is_key
        self.priority = priority

    def append_to_element(self, element: Xml.Element):
        sub = Xml.SubElement(element, 'item', attrib={'priority': str(self.priority)})
        if self.is_key:
            sub.attrib['key'] = 'true'
        self.content.append_to_element(sub)

    @staticmethod
    def parse_xml_element(element: Xml.Element) -> 'OptionItem':
        if _get_simple_tag_name(element) != 'item':
            raise TypeError(f'Unexpected tag {_get_simple_tag_name(element)}')
        if len(element) != 1:
            raise TypeError(f'Unexpected {len(element)} children tag')

        return OptionItem(
            content=ArchiveFrame.parse_xml_element(element[0]),
            is_key='key' in element.attrib and element.attrib['key'] == 'true',
            priority=_get_attribute_safe(element, 'priority', int)
        )

    def __hash__(self):
        return hash(self.is_key) * 31 + self.priority * 31 + hash(self.content)

    def __eq__(self, other):
        return isinstance(other, OptionItem) and other.content == self.content \
            and other.is_key == self.is_key \
            and other.priority == self.priority


class Options(ArchiveFrame):
    content: set[OptionItem]
    name: str | None

    def __init__(self, content: set[OptionItem] | list[OptionItem], name: str | None = None):
        self.content = content if isinstance(content, set) else set(content)
        self.name = name

    def append_to_element(self, element: Xml.Element):
        sub = Xml.SubElement(element, 'options')
        for item in self.content:
            item.append_to_element(sub)

    @staticmethod
    def parse_xml_element(element: Xml.Element) -> 'ArchiveFrame':
        if _get_simple_tag_name(element) != 'options':
            raise TypeError(f'Unexpected tag {_get_simple_tag_name(element)}')

        return Options(
            content=list(OptionItem.parse_xml_element(e) for e in element if _get_simple_tag_name(e) == 'item'),
            name=element.attrib['name'] if 'name' in element.attrib else None
        )

    def __hash__(self):
        return hash(self.content) * 31 + hash(self.name)

    def __eq__(self, other):
        return isinstance(other, Options) \
            and other.content == self.content \
            and other.name == self.name


class Dimension:
    name: str
    __intensity: float

    @property
    def intensity(self):
        return self.__intensity

    @intensity.setter
    def intensity(self, value: float):
        if value > 1 or value <= 0:
            raise ValueError('intensity must fall in range of (0, 1]')
        self.__intensity = value

    def append_to_element(self, element: Xml.Element):
        sub = Xml.SubElement(element, 'dimension', attrib={'name': self.name})
        sub.text = str(self.intensity)

    def __init__(self, name: str, intensity: float):
        self.name = name
        self.intensity = intensity

    def __hash__(self):
        return hash(self.name) * 31 + hash(self.__intensity)

    def __eq__(self, other):
        return isinstance(other, Dimension) \
            and other.name == self.name \
            and other.__intensity == self.__intensity

    @staticmethod
    def parse_xml_element(element: Xml.Element) -> 'Dimension':
        if _get_simple_tag_name(element) != 'dimension':
            raise TypeError(f'Unexpected tag {_get_simple_tag_name(element)}')

        return Dimension(
            name=_get_attribute_safe(element, 'name'),
            intensity=float(element.text)
        )


class Quiz:
    name: str | None
    creation_time: datetime
    modification_time: datetime | None
    frames: list[ArchiveFrame]
    dimensions: set[Dimension]

    def __init__(self, frames: list[ArchiveFrame], dimensions: set[Dimension] | list[Dimension],
                 name: str | None, creation_time: datetime | None = None, modification_time: datetime | None = None):
        self.name = name
        self.creation_time = creation_time if creation_time is not None else datetime.now(UTC)
        self.modification_time = modification_time
        self.frames = frames
        self.dimensions = dimensions if isinstance(dimensions, set) else set(dimensions)

    def append_to_element(self, element: Xml.Element):
        sub = Xml.SubElement(element, 'quiz',
                             attrib={'name': self.name, 'creation': self.creation_time.isoformat()})
        if self.modification_time:
            sub.attrib['modification'] = self.modification_time.isoformat()

        frames_element = Xml.SubElement(sub, 'frames')
        for frame in self.frames:
            frame.append_to_element(frames_element)

        for dimension in self.dimensions:
            dimension.append_to_element(sub)

    @staticmethod
    def parse_xml_element(element: Xml.Element) -> 'Quiz':
        if _get_simple_tag_name(element) != 'quiz':
            raise TypeError(f'Unexpected tag {_get_simple_tag_name(element)}')

        frames_iter = (e for e in element if _get_simple_tag_name(e) == 'frames')
        try:
            frames_element = next(frames_iter)
        except StopIteration:
            raise TypeError('Expected one frames child, got none')

        try:
            next(frames_iter)
            raise TypeError('Unexpected multi-frames-children tag')
        except StopIteration:
            pass

        return Quiz(
            name=element.attrib['name'] if 'name' in element.attrib else None,
            creation_time=_get_attribute_safe(element, 'creation', datetime.fromisoformat),
            modification_time=datetime.fromisoformat(
                element.attrib['modification']) if 'modification' in element.attrib else None,
            dimensions=list(Dimension.parse_xml_element(e) for e in element if _get_simple_tag_name(e) == 'dimension'),
            frames=list(ArchiveFrame.parse_xml_element(e) for e in frames_element)
        )

    def __eq__(self, other):
        return isinstance(other, Quiz) and other.name == self.name \
            and other.creation_time == self.creation_time \
            and other.modification_time == self.modification_time \
            and other.frames == self.frames \
            and other.dimensions == self.dimensions


class QuizContainer:
    creation_time: datetime
    content: list[Quiz]

    def __init__(self, content: list[Quiz], creation_time: datetime | None = None):
        self.content = content
        self.creation_time = creation_time if creation_time is not None else datetime.now(UTC)

    def to_xml_element(self) -> Xml.Element:
        doc = Xml.Element('archive', attrib={'xmlns': NAMESPACE,
                                             'creation': self.creation_time.isoformat()})
        for quiz in self.content:
            quiz.append_to_element(doc)
        return doc

    def to_xml_document(self) -> bytes:
        ele = self.to_xml_element()
        return Xml.tostring(ele, xml_declaration=True, encoding='utf-8')

    def __eq__(self, other):
        return isinstance(other, QuizContainer) \
            and other.content == self.content \
            and other.creation_time == self.creation_time

    @staticmethod
    def parse_xml_element(element: Xml.Element) -> 'QuizContainer':
        if _get_simple_tag_name(element) != 'archive':
            raise TypeError(f'Unexpected tag {_get_simple_tag_name(element)}')

        return QuizContainer(
            creation_time=_get_attribute_safe(element, 'creation', datetime.fromisoformat),
            content=list(Quiz.parse_xml_element(e) for e in element if _get_simple_tag_name(e) == 'quiz')
        )